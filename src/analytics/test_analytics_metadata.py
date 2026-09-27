import copy
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

import main
from src.analytics.business import calcular_kpis
from src.analytics.column_mapper import mapear_colunas
from src.quality.validator import gerar_diagnostico


class AnalyticsMetadataTests(unittest.TestCase):
    def frame(self):
        df = pd.DataFrame({
            "Data": pd.to_datetime(["2020-01-02", "2020-02-03"]),
            "Cliente": ["Empresa ABC", "EMPRESA ABC"],
            "Valor_Total": [100., 100.],
            "Valor_Com_Desconto": [100., 300.],
            "Margem_Bruta": [20., 30.],
            "Margem_Bruta_Percentual": [20., 10.],
        })
        df.attrs["mapeamentos_automaticos"] = {"coluna_3": "valor_total"}
        df.attrs["mapeamentos_confirmados"] = {
            "coluna_4": "valor_com_desconto", "coluna_7": "margem_bruta",
            "coluna_8": "margem_bruta_percentual",
        }
        df.attrs["mapeamento_semantico_usuario"] = [{"coluna": "coluna_4", "conceito": "valor_com_desconto"}]
        df.attrs["outro_metadado"] = {"preservar": True}
        df.attrs["ingestao"] = {"cabecalho_detectado": True, "normalizacao": {
            "auditoria_linhas": [{"linha": i, "classificacao": "transaction"} for i in range(100)],
            "blocos": [{"linhas_origem": [2, 3]}],
            "evidencias_excel": {"formulas": [
                {"linha": 2, "coluna": 8, "formula": "=G2/D2"},
                {"linha": 3, "coluna": 8, "formula": "=G3/D3"},
            ]},
        }}
        return df

    def test_formula_and_mapping_match_with_external_ingestion_metadata(self):
        for multiple_files in (False, True):
            with self.subTest(multiple_files=multiple_files):
                original = self.frame()
                if multiple_files:
                    original.attrs["ingestao"] = {"vendas": original.attrs["ingestao"]}
                before_attrs = copy.deepcopy(original.attrs)
                expected = calcular_kpis(original)
                light = original.copy()
                ingestion = light.attrs.pop("ingestao")
                actual = calcular_kpis(light, ingestao=ingestion)
                self.assertEqual(actual, expected)
                self.assertEqual(actual["margem_bruta_percentual"], 12.5)
                self.assertEqual(actual["margem_bruta_percentual_linhas_base"], 2)
                self.assertEqual(mapear_colunas(light), mapear_colunas(original))
                self.assertEqual(original.attrs, before_attrs)

    def continue_analysis(self, frame):
        context = {
            "diagnostico": gerar_diagnostico(frame), "problemas": [], "logs_etl": [],
            "arquivos_analisados": [], "analysis_id": None,
            "automatic_mappings": frame.attrs.get("mapeamentos_automaticos", {}),
            "semantic_mappings": frame.attrs.get("mapeamentos_confirmados", {}),
        }
        before_context = copy.deepcopy(context)
        seen_attrs = []
        analyze_customers = main.analisar_clientes
        def capture(dataframe):
            seen_attrs.append(copy.deepcopy(dataframe.attrs))
            return analyze_customers(dataframe)
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            with patch("main.analisar_clientes", side_effect=capture):
                summary = main.continuar_analytics(frame, context, Path(folder), {"candidates": []})
        self.assertEqual(context, before_context)
        return summary, seen_attrs[0]

    def test_full_continuation_preserves_audit_and_other_attrs(self):
        frame = self.frame()
        original = frame.copy(deep=True)
        original_attrs = copy.deepcopy(frame.attrs)
        summary, attrs = self.continue_analysis(frame)
        self.assertNotIn("ingestao", attrs)
        self.assertEqual(attrs, {key: value for key, value in original_attrs.items() if key != "ingestao"})
        self.assertEqual(summary["dados"]["ingestao"], original_attrs["ingestao"])
        self.assertEqual(summary["dados"]["mapeamento_semantico"]["confirmado_pelo_usuario"], original_attrs["mapeamentos_confirmados"])
        self.assertEqual(summary["kpis"]["margem_bruta_percentual"], 12.5)
        assert_frame_equal(frame, original)
        self.assertEqual(frame.attrs, original_attrs)

    def test_missing_ingestion_metadata_uses_full_continuation(self):
        frame = self.frame()
        frame.attrs.pop("ingestao")
        expected = calcular_kpis(frame)
        summary, attrs = self.continue_analysis(frame)
        self.assertEqual(attrs, frame.attrs)
        self.assertEqual(summary["kpis"]["valor_total"], expected["valor_total"])
        self.assertEqual(summary["dados"]["ingestao"], {})
        self.assertEqual(summary["clientes"]["quantidade_clientes"], 2)

    def test_legacy_kpi_call_still_reads_ingestion_attrs(self):
        frame = self.frame()
        self.assertEqual(calcular_kpis(frame)["margem_bruta_percentual"], 12.5)
        for metadata in [None, [], "unknown"]:
            with self.subTest(metadata=metadata):
                frame.attrs["ingestao"] = metadata
                self.assertEqual(calcular_kpis(frame), calcular_kpis(frame, ingestao=metadata))
