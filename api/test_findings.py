import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from src.analytics.finding_selection import selecionar_achados_principais


class FindingApiTests(unittest.TestCase):
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
        csv = b"Pedido,Cliente,Faturamento,Lucro\n1,Empresa ABC,100,-5\n2,EMPRESA ABC,50,20\n3,Outra,200,60\n"
        response = self.client.post("/api/analysis", files=[("files", ("vendas.csv", csv))])
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["summary"]

    def test_new_findings_persist_and_merge_recalculates_same_event(self):
        before = self.upload()
        identifier = before["analysis_id"]
        concentration = next(f for f in before["achados_analiticos"] if f["rule"] == "customer_concentration")
        candidate = before["dados"]["entity_resolution"]["candidates"][0]
        response = self.client.post(f"/api/analysis/{identifier}/entities",
                                    json={"candidate_id": candidate["candidate_id"], "decision": "merge"})
        self.assertEqual(response.status_code, 200, response.text)
        after = response.json()["summary"]
        updated = next(f for f in after["achados_analiticos"] if f["rule"] == "customer_concentration")
        self.assertEqual(updated["id"], concentration["id"])
        self.assertNotEqual(updated["evidence"], concentration["evidence"])
        self.assertEqual(before["kpis"], after["kpis"])
        self.assertFalse(any(f["rule"] == "negative_results" and f["scope"] == "customers"
                             for f in after["achados_analiticos"]))
        self.assertTrue(any(f["scope"] == "records" for f in after["achados_analiticos"]))
        self.client.close()
        self.client = TestClient(create_app(self.report, self.uploads))
        self.assertEqual(self.client.get(f"/api/analysis/{identifier}").json(), after)
        self.assertEqual(self.client.get("/api/analysis/latest").json(), after)
        self.assertEqual(json.loads(self.report.read_text(encoding="utf-8")), after)

    def test_old_snapshot_without_findings_is_read_without_recalculation(self):
        summary = self.upload()
        identifier = summary["analysis_id"]
        summary.pop("achados_analiticos")
        summary.pop("achados_principais")
        detail = self.root / "data/analysis_history/details" / f"{identifier}.json"
        detail.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
        original = detail.read_bytes()
        with patch("main.gerar_achados_analiticos", side_effect=AssertionError("historico recalculado")):
            self.assertEqual(self.client.get(f"/api/analysis/{identifier}").json(), summary)
            self.assertEqual(self.client.get("/api/analysis/history").status_code, 200)
        self.assertEqual(detail.read_bytes(), original)

    def test_findings_are_additive_and_keep_separate_preserves_them(self):
        summary = self.upload()
        with patch("main.gerar_achados_analiticos", return_value=[]):
            without = self.upload()
        for key in ("kpis", "clientes", "produtos", "temporal", "riscos", "oportunidades",
                    "destaques", "principais_insights", "status_geral"):
            self.assertEqual(summary.get(key), without.get(key), key)
        self.assertEqual(without["achados_analiticos"], [])
        candidate = summary["dados"]["entity_resolution"]["candidates"][0]
        response = self.client.post(f"/api/analysis/{summary['analysis_id']}/entities",
                                    json={"candidate_id": candidate["candidate_id"], "decision": "keep_separate"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["summary"]["achados_analiticos"], summary["achados_analiticos"])
        self.assertEqual(response.json()["summary"]["achados_principais"], summary["achados_principais"])

    def test_temporal_findings_preserve_null_percentage_and_survive_history_read(self):
        csv = b"Pedido,Data,Faturamento,Lucro\n1,15/01/2026,1,-100\n2,15/02/2026,100000,-50\n"
        response = self.client.post("/api/analysis", files=[("files", ("temporal.csv", csv))])
        self.assertEqual(response.status_code, 200, response.text)
        summary = response.json()["summary"]
        temporal = [item for item in summary["achados_analiticos"] if item["scope"] == "temporal"]
        self.assertEqual(len(temporal), 2)
        for item in temporal:
            comparison = item["comparison"]
            self.assertIsNone(comparison["percentage_change"])
            self.assertEqual(comparison["absolute_change"], 99999 if item["metric"] == "faturamento" else 50)
            self.assertEqual(comparison["reason"], "low_reference_base" if item["metric"] == "faturamento" else "negative_reference")
        self.assertIsNone(summary["temporal"]["evolucao_metrica"])
        json.dumps(summary, allow_nan=False)
        with patch("main.gerar_achados_analiticos", side_effect=AssertionError("historico recalculado")):
            self.assertEqual(self.client.get(f"/api/analysis/{summary['analysis_id']}").json(), summary)

    def test_entity_findings_merge_keep_separate_and_history(self):
        csv = ("Pedido,Data,Cliente,Valor_Total\n"
               "1,15/01/2026,Empresa ABC,50\n2,15/02/2026,Empresa ABC,20\n"
               "3,15/01/2026,EMPRESA ABC,30\n4,15/02/2026,EMPRESA ABC,20\n"
               "5,15/01/2026,Outra Empresa,20\n6,15/02/2026,Outra Empresa,30\n").encode()
        for decision in ("merge", "keep_separate"):
            response = self.client.post("/api/analysis", files=[("files", ("carteira.csv", csv))])
            self.assertEqual(response.status_code, 200, response.text)
            before = response.json()["summary"]
            identifier = before["analysis_id"]
            route = f"/api/analysis/{identifier}/entities"
            candidate = next(c for c in before["dados"]["entity_resolution"]["candidates"]
                             if {c["left"]["value"], c["right"]["value"]} == {"Empresa ABC", "EMPRESA ABC"})
            payload = {"candidate_id": candidate["candidate_id"], "decision": decision}
            with patch("src.quality.entity_resolution.detectar_entidades", side_effect=AssertionError("fuzzy")):
                response = self.client.post(route, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            after = response.json()["summary"]
            findings = [f for f in after["achados_analiticos"] if f["entity"]]
            self.assertTrue(findings)
            self.assertEqual(before["kpis"], after["kpis"])
            self.assertEqual(before["temporal"], after["temporal"])
            self.assertEqual(after["achados_principais"], selecionar_achados_principais(after["achados_analiticos"]))
            if decision == "merge":
                item = next(f for f in findings if f["entity"]["value"] == "Empresa ABC")
                self.assertEqual(item["comparison"]["previous_value"], 80)
                self.assertEqual(item["comparison"]["current_value"], 40)
                self.assertEqual(item["entity"]["identity_source"], "confirmed_alias")
                self.assertNotIn("EMPRESA ABC", {f["entity"]["value"] for f in findings})
            else:
                self.assertEqual(before["achados_analiticos"], after["achados_analiticos"])
            self.assertEqual(self.client.post(route, json=payload).json()["summary"], after)
            self.client.close()
            self.client = TestClient(create_app(self.report, self.uploads))
            with patch("main.agregar_entidades_periodo", side_effect=AssertionError("historico recalculado")):
                self.assertEqual(self.client.get(f"/api/analysis/{identifier}").json(), after)

    def test_products_entity_findings_are_additive_and_persisted(self):
        csv = ("Pedido,Data,Produto_ID,Produto,Faturamento\n"
               "1,15/01/2026,1,Papel,50\n2,15/02/2026,1,Papel Azul,20\n"
               "3,15/01/2026,2,Caneta,20\n4,15/02/2026,2,Caneta,30\n").encode()
        response = self.client.post("/api/analysis", files=[("files", ("produtos.csv", csv))])
        self.assertEqual(response.status_code, 200, response.text)
        summary = response.json()["summary"]
        items = [f for f in summary["achados_analiticos"] if f["scope"] == "products"]
        self.assertEqual({f["rule"] for f in items}, {"product_contributor_decline", "product_growth"})
        self.assertTrue(all(f["entity"]["id"] is not None for f in items))
        self.assertEqual(self.client.get(f"/api/analysis/{summary['analysis_id']}").json(), summary)
        json.dumps(summary, allow_nan=False)

    def test_executive_selection_is_additive_in_analysis_latest_detail_and_report(self):
        summary = self.upload()
        expected = selecionar_achados_principais(summary["achados_analiticos"])
        self.assertTrue(expected)
        self.assertEqual(summary["achados_principais"], expected)
        self.assertEqual(self.client.get("/api/analysis/latest").json()["achados_principais"], expected)
        self.assertEqual(self.client.get(f"/api/analysis/{summary['analysis_id']}").json()["achados_principais"], expected)
        report = json.loads((self.root / "reports/analise.json").read_text(encoding="utf-8"))
        self.assertEqual(report["achados_principais"], expected)
        self.assertEqual(report["achados_analiticos"], summary["achados_analiticos"])
        with patch("main.selecionar_achados_principais", return_value=[]):
            without = self.upload()
        for key in ("kpis", "clientes", "produtos", "temporal", "principais_riscos", "oportunidades",
                    "principais_insights", "status_geral"):
            self.assertEqual(summary.get(key), without.get(key), key)
        self.assertEqual(without["achados_principais"], [])

    def test_stage_four_snapshot_without_selection_is_not_recomputed(self):
        summary = self.upload()
        summary.pop("achados_principais")
        identifier = summary["analysis_id"]
        detail = self.root / "data/analysis_history/details" / f"{identifier}.json"
        detail.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
        before = detail.read_bytes()
        with patch("main.selecionar_achados_principais", side_effect=AssertionError("historico recalculado")):
            self.assertEqual(self.client.get(f"/api/analysis/{identifier}").json(), summary)
            self.assertEqual(self.client.get("/api/analysis/history").status_code, 200)
        self.assertEqual(detail.read_bytes(), before)
