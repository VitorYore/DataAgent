import unittest
from contextlib import redirect_stdout
import io
import tempfile
from pathlib import Path

import pandas as pd

from src.analytics.assisted_mapping import (
    aplicar_mapeamento_completo,
    perfilar_colunas,
    precisa_mapeamento,
    validar_mapeamentos,
)


class AssistedMappingTests(unittest.TestCase):
    def frame(self):
        frame = pd.DataFrame({
            "coluna_1": ["02/01/2017", "05/01/2017", "06/01/2017"],
            "coluna_2": ["Cliente A", "Cliente B", "Cliente C"],
            "coluna_3": [1204.2, 50.7, 189.4],
        })
        frame.attrs["ingestao"] = {"normalizacao": {"estrutura_detectada": "relatorio_operacional"}}
        return frame

    def test_perfil_reconhece_data_sem_assumir_semantica_financeira(self):
        frame = self.frame()
        ask, columns, required, automatic = precisa_mapeamento(frame)
        self.assertTrue(ask)
        self.assertEqual(automatic, {"coluna_1": "data"})
        self.assertEqual(len(columns[0]["exemplos"]), 3)
        self.assertEqual(columns[2]["papel_estrutural"], "valor_monetario")
        self.assertIsNone(columns[2]["conceito_semantico"])
        self.assertEqual({item["coluna"] for item in required}, {"coluna_2", "coluna_3"})

    def test_tabela_convencional_nao_pede_confirmacao(self):
        frame = pd.DataFrame({"Data": pd.to_datetime(["2025-01-01"]), "Faturamento": [100.0]})
        self.assertFalse(precisa_mapeamento(frame)[0])

    def test_validacao_exige_decisao_e_bloqueia_tipos_incompativeis(self):
        frame = self.frame()
        with self.assertRaisesRegex(ValueError, "Defina um significado"):
            validar_mapeamentos(frame, {"coluna_3": "faturamento"})
        with self.assertRaisesRegex(ValueError, "incompatível"):
            validar_mapeamentos(frame, {"coluna_2": "faturamento", "coluna_3": "cliente"})

    def test_mapping_aplica_rename_ignorar_e_preserva_auditoria(self):
        frame = self.frame()
        mapping = {"coluna_2": "cliente", "coluna_3": "faturamento"}
        confirmed = validar_mapeamentos(frame, mapping)
        result, audit = aplicar_mapeamento_completo(frame, {"coluna_1": "data"}, confirmed)
        self.assertEqual(list(result.columns), ["Data", "Cliente", "Faturamento"])
        self.assertEqual(len(audit), 3)
        self.assertEqual(result.attrs["mapeamentos_confirmados"], mapping)

    def test_identificador_nao_e_chamado_pedido_automaticamente(self):
        frame = self.frame()
        frame["coluna_4"] = [101, 102, 103]
        columns, required, automatic = perfilar_colunas(frame)
        identifier = next(item for item in columns if item["nome"] == "coluna_4")
        self.assertEqual(identifier["conceito_semantico"], "identificador")
        self.assertEqual(identifier["estado"], "provavel")
        self.assertNotIn("coluna_4", automatic)
        self.assertIn("pedido", next(item for item in required if item["coluna"] == "coluna_4")["conceitos_compativeis"])

    def test_data_de_alta_confianca_converte_invalidos_com_auditoria(self):
        dates = pd.date_range("2017-01-01", periods=19).strftime("%d/%m/%Y").tolist() + ["conteúdo inválido"]
        frame = pd.DataFrame({
            "coluna_1": dates,
            "coluna_2": [f"Cliente {index}" for index in range(20)],
            "coluna_3": [index + 0.25 for index in range(20)],
        })
        result, audit = aplicar_mapeamento_completo(frame, {"coluna_1": "data"}, {
            "coluna_2": "cliente", "coluna_3": "faturamento",
        })
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["Data"]))
        self.assertTrue(pd.isna(result.loc[19, "Data"]))
        self.assertTrue(any(item["tipo"] == "conversao_data_com_valores_invalidos" for item in audit))

    def test_sem_kpis_nao_classifica_negocio_com_score_saudavel(self):
        from main import executar_pipeline_analitico
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            summary = executar_pipeline_analitico(pd.DataFrame({"comentario": ["A", "B", "C"]}), "fixture.csv", Path(directory))
        self.assertIsNone(summary["status_geral"]["score"])
        self.assertIsNone(summary["status_geral"]["status"])
        self.assertEqual(summary["suficiencia_analitica"], "insuficiente")


if __name__ == "__main__":
    unittest.main()
