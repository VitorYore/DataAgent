import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import xlwt
from fastapi.testclient import TestClient

from api.app import create_app
from main import executar_dataagent

CSV = b"pedido_id,data,produto,cliente,quantidade,preco_unitario,custo_unitario\n1,2025-01-15,Produto A,Cliente A,2,100,30\n2,2025-02-15,Produto B,Cliente B,3,200,50\n3,2025-03-15,Produto A,Cliente A,1,100,30\n"


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.report = self.root / "reports/resumo_executivo.json"
        self.uploads = self.root / "data/uploads"
        self.app = create_app(self.report, self.uploads)
        self.client = TestClient(self.app)
        self.logs = redirect_stdout(io.StringIO())
        self.logs.__enter__()

    def tearDown(self):
        self.logs.__exit__(None, None, None)
        self.client.close()
        self.temporary.cleanup()

    def post(self, files):
        return self.client.post("/api/analysis", files=[("files", (name, content)) for name, content in files])

    def test_csv_result_latest_and_isolation(self):
        self.assertEqual(self.client.get("/api/analysis/status").json(), {"status": "idle"})
        result = self.post([("vendas.csv", CSV)])
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["files_processed"], 1)
        summary = result.json()["summary"]
        self.assertEqual(summary["kpis"]["faturamento_total"], 900)
        self.assertEqual(self.client.get("/api/analysis/latest").json(), summary)
        self.assertEqual(json.loads(self.report.read_text(encoding="utf-8")), summary)
        self.assertEqual(self.client.get("/api/analysis/status").json(), {"status": "completed"})
        self.assertEqual(list(self.uploads.iterdir()), [])
        # A segunda requisição usa somente seu arquivo, sem reaproveitar o primeiro.
        result = self.post([("outras_vendas.csv", CSV.replace(b",100,30", b",200,30"))])
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["summary"]["kpis"]["faturamento_total"], 1200)
        self.assertEqual(result.json()["files_processed"], 1)

    def test_excel_xlsx_and_xls(self):
        data = pd.read_csv(io.BytesIO(CSV))
        xlsx = io.BytesIO()
        data.to_excel(xlsx, index=False)
        book = xlwt.Workbook()
        sheet = book.add_sheet("Vendas")
        for column, name in enumerate(data.columns):
            sheet.write(0, column, name)
        for row, values in enumerate(data.itertuples(index=False, name=None), start=1):
            for column, value in enumerate(values):
                sheet.write(row, column, value)
        xls = io.BytesIO()
        book.save(xls)
        for extension, content in [("xlsx", xlsx.getvalue()), ("xls", xls.getvalue())]:
            with self.subTest(extension=extension):
                result = self.post([(f"vendas.{extension}", content)])
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()["summary"]["kpis"]["faturamento_total"], 900)

    def test_multitable_equals_shared_pipeline(self):
        source = Path(__file__).resolve().parents[1] / "data/samples"
        # Amostras reais; preserva nomes para o detector/merger/enricher.
        files = []
        for name, limit in [("Historico_Vendas.csv", 40), ("Produtos.csv", 1000), ("Clientes.csv", 1000)]:
            files.append((name, pd.read_csv(source / name).head(limit).to_csv(index=False).encode("utf-8")))
        inputs = self.root / "cli-input"
        inputs.mkdir()
        for name, content in files:
            (inputs / name).write_bytes(content)
        expected = executar_dataagent(inputs, self.root / "cli-output", estrito=True)
        result = self.post(files)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["files_processed"], 3)
        self.assertEqual(result.json()["summary"]["kpis"], expected["kpis"])
        self.assertEqual(result.json()["summary"]["produtos"], expected["produtos"])

    def test_invalid_requests_and_previous_summary(self):
        previous = self.post([("vendas.csv", CSV)]).json()["summary"]
        cases = [
            ([], 400),
            ([("run.py", CSV)], 400),
            ([("../vendas.csv", CSV)], 400),
            ([("a.csv", b"")], 400),
            ([("a.csv", b'a,b\n"unfinished')], 422),
            ([("a.xlsx", b"not an excel file")], 422),
            ([("a.xls", b"invalid")], 422),
            ([("a.csv", b"a,b\n")], 422),
            ([("a.csv", CSV), ("a.xlsx", CSV)], 400),
            ([("vendas.csv", CSV), ("bad.csv", b'a,b\n"unfinished')], 422),
            ([("first.csv", b"foo\na\nb"), ("second.csv", b"bar\nx\ny")], 422),
        ]
        for files, code in cases:
            with self.subTest(files=[name for name, _ in files]):
                response = self.post(files)
                self.assertEqual(response.status_code, code, response.text)
                self.assertNotIn("Traceback", response.text)
                self.assertEqual(self.client.get("/api/analysis/latest").json(), previous)
                self.assertEqual(list(self.uploads.iterdir()), [])

    def test_concurrent_request_rejected_and_status(self):
        entered, release = threading.Event(), threading.Event()

        def blocked(*args, **kwargs):
            entered.set()
            release.wait(10)
            raise RuntimeError("test internal error")

        with patch("api.analysis.executar_dataagent", side_effect=blocked):
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(self.post, [("vendas.csv", CSV)])
                self.assertTrue(entered.wait(5))
                self.assertEqual(self.client.get("/api/analysis/status").json(), {"status": "processing"})
                try:
                    response = self.post([("vendas.csv", CSV)])
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(response.json(), {"detail": "Uma análise já está em andamento."})
                finally:
                    release.set()
                self.assertEqual(pending.result().status_code, 500)
        self.assertEqual(self.client.get("/api/analysis/status").json(), {"status": "error"})
        self.assertEqual(self.post([("vendas.csv", CSV)]).status_code, 200)

    def test_openapi_and_post_cors(self):
        self.assertIn("post", self.client.get("/openapi.json").json()["paths"]["/api/analysis"])
        response = self.client.options("/api/analysis", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)

    def test_etl_and_relationship_errors_keep_previous_summary(self):
        previous = self.post([("vendas.csv", CSV)]).json()["summary"]
        for function, files in [
            ("main.executar_etl", [("vendas.csv", CSV)]),
            ("main.detectar_relacionamentos", [("vendas.csv", CSV), ("outra.csv", b"id,nome\n1,A")]),
        ]:
            with self.subTest(function=function):
                with patch(function, side_effect=ValueError("test data failure")):
                    response = self.post(files)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(self.client.get("/api/analysis/latest").json(), previous)


if __name__ == "__main__":
    unittest.main()
