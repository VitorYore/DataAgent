import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.app import create_app

CSV = "Pedido,Data,Cliente,Valor_Total,Margem_Bruta\n1,2020-01-01,Empresa ABC,100,30\n2,2020-02-01,EMPRESA ABC,50,20\n3,2020-03-01,Outra Empresa,200,60\n".encode("utf-8")


class EntityApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = self.root / "reports/resumo_executivo.json"
        self.uploads = self.root / "data/uploads"
        self.client = TestClient(create_app(self.report, self.uploads))
        self.logs = redirect_stdout(io.StringIO())
        self.logs.__enter__()

    def tearDown(self):
        self.logs.__exit__(None, None, None)
        self.client.close()
        self.temp.cleanup()

    def upload(self):
        response = self.client.post("/api/analysis", files=[("files", ("vendas.csv", CSV))])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "success")
        return response.json()["summary"]

    def test_candidates_are_readable_from_latest_history_and_after_restart(self):
        summary = self.upload()
        report = summary["dados"]["entity_resolution"]
        self.assertEqual(report["total_candidates"], 1)
        self.assertEqual(report["candidates"][0]["combined_preview"], 150)
        self.assertEqual(summary["clientes"]["quantidade_clientes"], 3)
        self.assertEqual(summary["kpis"]["valor_total"], 350)
        self.assertEqual(json.loads(self.report.read_text(encoding="utf-8")), summary)
        self.client.close()
        self.client = TestClient(create_app(self.report, self.uploads))
        self.assertEqual(self.client.get("/api/analysis/latest").json(), summary)
        self.assertEqual(self.client.get("/api/analysis/" + summary["analysis_id"]).json(), summary)
        self.assertEqual(len(self.client.get("/api/analysis/history").json()), 1)
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertEqual(set(paths["/api/analysis/{analysis_id}/entities"]), {"get", "post"})

    def test_detection_does_not_change_kpis_rankings_quality_or_processed_data(self):
        detected = self.upload()
        processed = (self.root / "data/processed/vendas_tratadas.csv").read_bytes()
        with patch("src.quality.entity_resolution.detectar_entidades", return_value={}):
            baseline = self.upload()
        for key in ("kpis", "clientes", "produtos", "temporal", "principais_insights"):
            self.assertEqual(detected.get(key), baseline.get(key), key)
        self.assertEqual(detected["dados"]["score_qualidade"], baseline["dados"]["score_qualidade"])
        self.assertEqual(processed, (self.root / "data/processed/vendas_tratadas.csv").read_bytes())

    def test_merge_restart_history_preserves_kpis_and_intermediate(self):
        import hashlib
        summary = self.upload()
        identifier = summary["analysis_id"]
        route = f"/api/analysis/{identifier}/entities"
        report = self.client.get(route).json()
        candidate = report["candidates"][0]
        archive = self.root / "data/analysis_history/working" / identifier / "entity_analysis.pkl"
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        csv_before = (self.root / "data/processed/vendas_tratadas.csv").read_bytes()
        created = self.client.get("/api/analysis/history").json()[0]["created_at"]
        with patch("api.analysis.executar_dataagent", side_effect=AssertionError("ingestao")), patch("main.executar_etl", side_effect=AssertionError("ETL")), patch("src.quality.entity_resolution.detectar_entidades", side_effect=AssertionError("detector")):
            response = self.client.post(route, json={"candidate_id": candidate["candidate_id"], "decision": "merge"})
        self.assertEqual(response.status_code, 200, response.text)
        after = response.json()["summary"]
        self.assertEqual(after["clientes"]["quantidade_clientes"], 2)
        for key in ("kpis", "temporal"):
            self.assertEqual(after.get(key), summary.get(key))
        self.assertEqual(after["dados"]["score_qualidade"], summary["dados"]["score_qualidade"])
        self.assertEqual(after["dados"]["entity_resolution"]["decisions"][0]["origin"], "user_confirmation")
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), digest)
        self.assertEqual(csv_before, (self.root / "data/processed/vendas_tratadas.csv").read_bytes())
        self.client.close()
        self.client = TestClient(create_app(self.report, self.uploads))
        self.assertEqual(self.client.get(route).json()["candidates"][0]["status"], "merged")
        self.assertEqual(self.client.get(f"/api/analysis/{identifier}").json(), after)
        self.assertEqual(self.client.get("/api/analysis/latest").json(), after)
        self.assertEqual(self.client.get("/api/analysis/history").json()[0]["created_at"], created)
        repeated = self.client.post(route, json={"candidate_id": candidate["candidate_id"], "decision": "merge"})
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()["summary"], after)
        self.assertEqual(self.client.post(route, json={"candidate_id": candidate["candidate_id"], "decision": "keep_separate"}).status_code, 422)

    def test_keep_separate_on_old_analysis_does_not_replace_latest(self):
        old = self.upload()
        latest = self.upload()
        route = f"/api/analysis/{old['analysis_id']}/entities"
        candidate = self.client.get(route).json()["candidates"][0]
        with patch("api.analysis.continuar_analytics", side_effect=AssertionError("analytics desnecessario")):
            response = self.client.post(route, json={"candidate_id": candidate["candidate_id"], "decision": "keep_separate"})
        self.assertEqual(response.status_code, 200, response.text)
        after = response.json()["summary"]
        self.assertEqual(after["clientes"], old["clientes"])
        self.assertEqual(after["dados"]["entity_resolution"]["candidates"][0]["status"], "kept_separate")
        self.assertEqual(self.client.get("/api/analysis/latest").json(), latest)
        self.assertEqual(self.client.get(f"/api/analysis/{old['analysis_id']}").json(), after)

    def test_invalid_requests_are_rejected(self):
        a = self.upload()
        b = self.upload()
        route = f"/api/analysis/{a['analysis_id']}/entities"
        c = a["dados"]["entity_resolution"]["candidates"][0]["candidate_id"]
        foreign = b["dados"]["entity_resolution"]["candidates"][0]["candidate_id"]
        for payload in [{}, {"candidate_id": "missing", "decision": "merge"},
                        {"candidate_id": foreign, "decision": "merge"},
                        {"candidate_id": c, "decision": "invented"},
                        {"candidate_id": c, "decision": "merge", "canonical_value": "arbitrary"},
                        {"candidate_id": c, "decision": "merge", "entity_type": "produto"}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post(route, json=payload).status_code, 422)
        self.assertEqual(self.client.post("/api/analysis/missing/entities", json={"decision": "merge"}).status_code, 404)
        self.assertEqual(self.client.get("/api/analysis/..%2Fsecret/entities").status_code, 404)

    def test_old_snapshot_stays_readable(self):
        summary = self.upload()
        identifier = summary["analysis_id"]
        detail = self.root / "data/analysis_history/details" / (identifier + ".json")
        summary["dados"].pop("entity_resolution")
        detail.write_text(json.dumps(summary), encoding="utf-8")
        self.assertEqual(self.client.get(f"/api/analysis/{identifier}").json(), summary)
        self.assertEqual(self.client.get(f"/api/analysis/{identifier}/entities").json()["candidates"], [])

    def test_failure_or_changed_totals_does_not_publish_decision(self):
        summary = self.upload()
        route = f"/api/analysis/{summary['analysis_id']}/entities"
        candidate = summary["dados"]["entity_resolution"]["candidates"][0]
        report = self.client.get(route).json()
        for error in [ValueError("falha"), None]:
            changed = {**summary, "kpis": {"valor_total": 999}}
            with patch("api.analysis.continuar_analytics", side_effect=error, return_value=changed):
                response = self.client.post(route, json={"candidate_id": candidate["candidate_id"], "decision": "merge"})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(self.client.get(route).json(), report)
            self.assertEqual(self.client.get("/api/analysis/latest").json(), summary)

    def test_general_financial_totals_and_orders_unchanged(self):
        data = b"Pedido,Data,Cliente,Faturamento,Custo,Lucro\n1,2020-01-01,Empresa ABC,100,70,30\n2,2020-02-01,EMPRESA ABC,50,30,20\n"
        before = self.client.post("/api/analysis", files=[("files", ("vendas.csv", data))]).json()["summary"]
        candidate = before["dados"]["entity_resolution"]["candidates"][0]
        response = self.client.post(f"/api/analysis/{before['analysis_id']}/entities", json={"candidate_id": candidate["candidate_id"], "decision": "merge"})
        self.assertEqual(response.status_code, 200, response.text)
        after = response.json()["summary"]
        self.assertEqual(after["kpis"], before["kpis"])
        self.assertEqual(after["temporal"], before["temporal"])
        self.assertEqual(after["clientes"]["quantidade_clientes"], 1)

    def test_busy_and_missing_intermediate_are_safe(self):
        summary = self.upload()
        identifier = summary["analysis_id"]
        route = f"/api/analysis/{identifier}/entities"
        candidate = summary["dados"]["entity_resolution"]["candidates"][0]
        payload = {"candidate_id": candidate["candidate_id"], "decision": "merge"}
        runner = self.client.app.state.analysis_runner
        runner.lock.acquire()
        try:
            self.assertEqual(self.client.post(route, json=payload).status_code, 409)
        finally:
            runner.lock.release()
        archive = self.root / "data/analysis_history/working" / identifier / "entity_analysis.pkl"
        archive.unlink()
        self.assertFalse(self.client.get(route).json()["can_decide"])
        self.assertEqual(self.client.post(route, json=payload).status_code, 409)
        self.assertEqual(self.client.get("/api/analysis/latest").json(), summary)

    def test_csv_and_excel_sources_remain_intact_after_merge(self):
        import pandas as pd
        excel = io.BytesIO()
        pd.read_csv(io.BytesIO(CSV)).to_excel(excel, index=False)
        for name, content in [("original.csv", CSV), ("original.xlsx", excel.getvalue())]:
            with self.subTest(name=name):
                source = self.root / name
                source.write_bytes(content)
                with source.open("rb") as input_file:
                    response = self.client.post("/api/analysis", files=[("files", (name, input_file))])
                self.assertEqual(response.status_code, 200, response.text)
                before = response.json()["summary"]
                identifier = before["analysis_id"]
                candidate = before["dados"]["entity_resolution"]["candidates"][0]
                archive = self.root / "data/analysis_history/working" / identifier / "entity_analysis.pkl"
                intermediate = archive.read_bytes()
                processed = (self.root / "data/processed/vendas_tratadas.csv").read_bytes()
                response = self.client.post(f"/api/analysis/{identifier}/entities",
                                            json={"candidate_id": candidate["candidate_id"], "decision": "merge"})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(source.read_bytes(), content)
                self.assertEqual(archive.read_bytes(), intermediate)
                self.assertEqual((self.root / "data/processed/vendas_tratadas.csv").read_bytes(), processed)
                self.assertEqual(response.json()["summary"]["kpis"], before["kpis"])
