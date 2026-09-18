import unittest
import pandas as pd

from src.analytics.temporal_quality import analisar_anomalias_temporais
from src.analytics.customers import analisar_clientes
from src.analytics.performance import analisar_desempenho


class TemporalQualityTests(unittest.TestCase):
    def test_isolated_far_years_are_flagged_without_mutating_source(self):
        values = [pd.Timestamp(year, 4, 25) for year in [2017] * 60 + [2018] * 60 + [2019] * 60 + [2020] * 60 + [1017, 2048]]
        frame = pd.DataFrame({"Data": values})
        original = frame["Data"].copy()
        result = analisar_anomalias_temporais(frame, "Data")
        self.assertEqual(result["quantidade"], 2)
        self.assertEqual(result["periodo_predominante"]["ano_inicio"], 2017)
        self.assertEqual(result["periodo_predominante"]["ano_fim"], 2020)
        self.assertEqual(int(result["mask"].sum()), 240)
        pd.testing.assert_series_equal(frame["Data"], original)

    def test_weak_edge_years_are_flagged_when_the_dominant_span_is_overwhelming(self):
        dates = [pd.Timestamp(year, 5, 10) for year in [2017] * 60 + [2018] * 60 + [2019] * 60 + [2020] * 60]
        dates.extend([pd.Timestamp(2016, 1, 21), pd.Timestamp(2016, 6, 14)])
        result = analisar_anomalias_temporais(pd.DataFrame({"date": dates}), "date")
        self.assertEqual(result["quantidade"], 2)
        self.assertEqual(result["periodo_predominante"]["ano_inicio"], 2017)
        self.assertEqual(int(result["mask"].sum()), 240)

    def test_low_confidence_or_sparse_legitimate_range_keeps_all_dates(self):
        dates = [pd.Timestamp(2020, 1, 1)] * 80 + [pd.Timestamp(2025, 1, 1)] * 20
        result = analisar_anomalias_temporais(pd.DataFrame({"date": dates}), "date")
        self.assertEqual(result["quantidade"], 0)
        self.assertTrue(result["mask"].all())

    def test_temporal_profit_uses_mask_but_business_total_keeps_original_rows(self):
        dates = [pd.Timestamp(year, ((i % 12) + 1), 1) for year in [2017, 2018, 2019, 2020] for i in range(15)]
        dates.extend([pd.Timestamp(2048, 4, 1)])
        frame = pd.DataFrame({"Data": dates, "Lucro": [10.0] * len(dates)})
        profile = analisar_anomalias_temporais(frame, "Data")
        filtered = frame.loc[profile["mask"]]
        result = analisar_desempenho(frame, dados_temporais=filtered)
        self.assertEqual(result["lucro_total"], 610.0)
        self.assertNotIn("2048-04", result["lucro_mensal"])
        self.assertIn("2048-04", frame["Data"].dt.to_period("M").astype(str).values)

    def test_missing_dates_and_small_samples_are_not_excluded(self):
        frame = pd.DataFrame({"date": [pd.Timestamp(2018, 1, 1), None, pd.Timestamp(2048, 1, 1)]})
        result = analisar_anomalias_temporais(frame, "date")
        self.assertEqual(result["quantidade"], 0)
        self.assertTrue(result["mask"].all())


class CustomerSemanticMetricsTests(unittest.TestCase):
    def test_value_total_concentration_and_gross_margin_use_semantic_labels(self):
        frame = pd.DataFrame({
            "Cliente_ID": [1, 1, 2, 3, 4, 5, 6],
            "Cliente": ["A", "A", "B", "C", "D", "E", "F"],
            "Valor_Total": [40, 60, 100, 90, 80, 70, 60],
            "Margem_Bruta": [5, 4, -1, 30, 40, 50, 60],
        })
        result = analisar_clientes(frame)
        self.assertEqual(result["metrica_principal"]["conceito"], "valor_total")
        self.assertEqual(result["metrica_principal"]["label"], "Valor Total")
        self.assertEqual(result["participacao_maior_cliente"], 20.0)
        self.assertEqual(result["concentracao_top_5"], 88.0)
        self.assertEqual(result["participacao_maior_cliente_metrica"]["label"], "Valor Total")
        self.assertEqual(result["maior_margem_bruta"]["label"], "Margem Bruta")
        self.assertEqual(result["clientes_margem_bruta_negativa"], 1)
        self.assertTrue(any("Margem Bruta negativa" in text for text in result["insights_clientes"]))
        self.assertNotIn("maior_faturamento", result)
        self.assertNotIn("maior_lucro", result)
        self.assertTrue(any("Valor Total" in text for text in result["insights_clientes"]))

    def test_zero_negative_gross_margin_count_is_available(self):
        frame = pd.DataFrame({
            "Cliente": ["A", "B"],
            "Margem_Bruta": [20, 10],
        })
        result = analisar_clientes(frame)
        self.assertEqual(result["clientes_margem_bruta_negativa"], 0)
        self.assertIsNone(result["clientes_resultado_negativo"])


if __name__ == "__main__":
    unittest.main()
