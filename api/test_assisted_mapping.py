import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from api.app import create_app
from src.analytics.assisted_mapping import SemanticMappingRequired, perfilar_colunas


class AssistedMappingApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = self.root / "reports/resumo_executivo.json"
        self.uploads = self.root / "data/uploads"
        self.client = TestClient(create_app(self.report, self.uploads))
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()
        self.frame = pd.DataFrame({
            "coluna_1": ["02/01/2017", "05/01/2017", "06/01/2017"],
            "coluna_2": ["Cliente A", "Cliente B", "Cliente C"],
            "coluna_3": [1204.2, 50.7, 189.4],
        })
        self.frame.attrs["ingestao"] = {
            "arquivo": "relatorio.xlsx", "aba": "Dados", "cabecalho_detectado": False,
            "normalizacao": {"estrutura_detectada": "relatorio_operacional"},
        }

    def tearDown(self):
        self.stdout.__exit__(None, None, None)
        self.client.close()
        self.temp.cleanup()

    def start_pending(self):
        columns, required, automatic = perfilar_colunas(self.frame)
        error = SemanticMappingRequired(self.frame, columns, required, automatic)
        with patch("api.analysis.executar_dataagent", side_effect=error):
            return self.client.post("/api/analysis", files=[("files", ("relatorio.xlsx", b"synthetic fixture"))])

    def test_pending_survives_runner_restart_and_pipeline_resumes(self):
        first = self.start_pending()
        self.assertEqual(first.status_code, 200, first.text)
        pending = first.json()
        self.assertEqual(pending["status"], "mapping_required")
        self.assertTrue(pending["analysis_id"].startswith("analysis_"))
        self.assertLessEqual(max(len(item["exemplos"]) for item in pending["detected_columns"]), 3)
        self.assertTrue((self.uploads / pending["analysis_id"] / "working_dataframe.pkl").is_file())

        # Nova instância da aplicação recupera o contexto e o DataFrame persistidos.
        self.client.close()
        self.client = TestClient(create_app(self.report, self.uploads))
        recovered = self.client.get(f"/api/analysis/{pending['analysis_id']}/mapping")
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(recovered.json()["status"], "mapping_required")

        invalid = self.client.post(f"/api/analysis/{pending['analysis_id']}/mapping", json={
            "mappings": {"coluna_2": "faturamento", "coluna_3": "cliente"}
        })
        self.assertEqual(invalid.status_code, 422, invalid.text)

        completed = self.client.post(f"/api/analysis/{pending['analysis_id']}/mapping", json={
            "mappings": {"coluna_2": "cliente", "coluna_3": "faturamento"}
        })
        self.assertEqual(completed.status_code, 200, completed.text)
        result = completed.json()
        self.assertEqual(result["status"], "success")
        summary = result["summary"]
        self.assertEqual(summary["analysis_id"], pending["analysis_id"])
        self.assertAlmostEqual(summary["kpis"]["faturamento_total"], 1444.3)
        self.assertEqual(summary["dados"]["mapeamento_semantico"]["confirmado_pelo_usuario"], {
            "coluna_2": "cliente", "coluna_3": "faturamento"
        })
        self.assertTrue(any(item["tipo"] == "mapeamento_semantico_usuario" for item in summary["dados"]["transformacoes"]))
        self.assertFalse((self.uploads / pending["analysis_id"]).exists())
        self.assertEqual(self.client.get("/api/analysis/latest").json(), summary)
        self.assertEqual(len(self.client.get("/api/analysis/history").json()), 1)


if __name__ == "__main__":
    unittest.main()
