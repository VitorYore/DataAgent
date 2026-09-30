import json
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from src.analytics.temporal_comparison import comparar_valores, comparar_serie
from src.analytics.temporal import analisar_meses
from src.analytics.growth import analisar_crescimento, avaliar_evolucao_total
from src.analytics.performance import analisar_desempenho
from src.analytics.insights import gerar_insights
from src.analytics.opportunities import analisar_oportunidades
from src.analytics.findings import gerar_achados_analiticos, deduplicar_achados
from src.reports.executive_summary import gerar_resumo_temporal


def frame(values, column="Faturamento", periods=None, records=5):
    periods = periods or [str(p) for p in pd.period_range("2026-01", periods=len(values), freq="M")]
    return pd.DataFrame({"Data": pd.to_datetime([p + "-01" for p in periods for _ in range(records)]),
                         column: [value / records for value in values for _ in range(records)]})


def findings(values, column="Faturamento", periods=None, records=5):
    monthly = analisar_meses(frame(values, column, periods, records))
    return gerar_achados_analiticos(temporal=monthly, analysis_id="test")


class TemporalComparisonTests(unittest.TestCase):
    def test_numeric_cases(self):
        cases = [(100, 120, 20, 20, None), (100, 80, -20, -20, None),
                 (0, 100, 100, None, "zero_reference"), (100, 0, -100, -100, None),
                 (1, 100000, 99999, None, "low_reference_base"),
                 (-100, -50, 50, None, "negative_reference"),
                 (-100, -150, -50, None, "negative_reference"),
                 (-100, 100, 200, None, "negative_reference"),
                 (100, -100, -200, None, "sign_change"), (100, 100, 0, 0, None)]
        for before, after, delta, percentage, reason in cases:
            with self.subTest(before=before, after=after):
                result = comparar_valores(before, after)
                self.assertEqual(result["absolute_change"], delta)
                self.assertEqual(result["percentage_change"], percentage)
                self.assertEqual(result["percentage_valid"], percentage is not None)
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["direction"], "increase" if delta > 0 else "decrease" if delta < 0 else "stable")
                json.dumps(result, allow_nan=False)

    def test_invalid_numbers_and_overflow(self):
        for value in (None, float("nan"), float("inf"), -float("inf"), "invalid"):
            for before, after in [(value, 100), (100, value)]:
                result = comparar_valores(before, after)
                self.assertFalse(result["comparable"])
                self.assertIsNone(result["absolute_change"])
                json.dumps(result, allow_nan=False)
        self.assertFalse(comparar_valores(-1e308, 1e308)["comparable"])
        json.dumps(comparar_valores(1e308, 1e308), allow_nan=False)

    def test_month_quarter_year_continuity(self):
        for before, after, granularity, continuous in [
            ("2026-01", "2026-02", "M", True), ("2026-01", "2026-03", "M", False),
            ("2025-12", "2026-01", "M", True), ("2025-01", "2026-01", "M", False),
            ("2025Q4", "2026Q1", "Q", True), ("2026Q1", "2026Q3", "Q", False),
            ("2025", "2026", "Y", True), ("2024", "2026", "Y", False),
        ]:
            with self.subTest(before=before, after=after):
                result = comparar_valores(100, 120, previous_period=before, current_period=after,
                                          granularity=granularity, require_consecutive=True)
                self.assertEqual(result["continuous"], continuous)
                self.assertEqual(result["comparable"], continuous)
                self.assertEqual(result["absolute_change"], 20)
                self.assertEqual(result["percentage_change"], 20 if continuous else None)

    def test_invalid_duplicate_and_reversed_periods(self):
        for before, after in [("invalid", "2026-02"), ("2026-01", "2026-13"),
                              ("2026-01", "2026-01"), ("2026-02", "2026-01"), (None, "2026-01")]:
            result = comparar_valores(100, 120, previous_period=before, current_period=after)
            self.assertFalse(result["comparable"])
            self.assertEqual(result["reason"], "invalid_period")

    def test_observed_endpoints_can_be_compared_without_monthly_claim(self):
        result = comparar_valores(100, 80, previous_period="2026-01", current_period="2026-03")
        self.assertTrue(result["comparable"])
        self.assertFalse(result["continuous"])
        self.assertEqual(result["percentage_change"], -20)

    def test_unsorted_series_and_missing_values_do_not_bridge(self):
        comparisons = comparar_serie({"2026-03": 80, "2026-01": 100, "2026-02": None})
        self.assertEqual(len(comparisons), 2)
        self.assertTrue(all(c["percentage_change"] is None for c in comparisons))
        self.assertEqual(comparisons[0]["previous_period"], "2026-01")

    def test_local_reference_also_blocks_outlier_in_flat_small_series(self):
        comparisons = comparar_serie({"2026-01": 1, "2026-02": 1, "2026-03": 1, "2026-04": 100000})
        self.assertEqual(comparisons[-1]["reason"], "low_reference_base")

    def test_evolution_does_not_drop_missing_endpoints(self):
        self.assertIsNone(avaliar_evolucao_total(pd.Series([None, 100, 120]))["variacao_percentual"])
        result = avaliar_evolucao_total(pd.Series([100, 80], index=["2026-03", "2026-01"]))
        self.assertEqual(result["variacao_percentual"], 25)


class TemporalIntegrationTests(unittest.TestCase):
    def test_monthly_and_growth_use_identical_comparisons(self):
        for values, periods in [([100, 120], None), ([1, 100000], None), ([-100, -50], None),
                                 ([0, 100], None), ([100, 80], ["2026-01", "2026-03"])]:
            df = frame(values, periods=periods)
            monthly = analisar_meses(df)
            growth = analisar_crescimento(df)
            self.assertEqual(monthly["variacao_mensal"], growth["faturamento"]["variacoes"])
            self.assertEqual(monthly["comparacoes"], growth["faturamento"]["comparacoes"])

    def test_regression_no_giant_percentage_or_negative_growth_claim(self):
        for values in ([1, 100000], [-100, -50]):
            monthly = analisar_meses(frame(values, "Lucro"))
            self.assertIsNone(monthly["variacao_mensal"]["2026-02"])
            messages = gerar_insights({}, monthly, {}, {})
            text = json.dumps(messages, ensure_ascii=False)
            self.assertNotIn("9999900", text)
            self.assertNotIn("aumento de -50", text)
            self.assertFalse(any(item["categoria"] == "maior_crescimento" for item in messages))

    def test_regression_gap_breaks_decline_sequence(self):
        df = frame([100, 80, 60, 40], periods=["2026-01", "2026-02", "2026-04", "2026-05"])
        growth = analisar_crescimento(df)
        self.assertIsNone(growth["faturamento"]["variacoes"]["2026-04"])
        self.assertEqual(growth["faturamento"]["sequencias_queda"], [])
        opportunities = analisar_oportunidades(growth, {}, {}, {}, {})
        self.assertFalse(any("consecutiv" in item["mensagem"] for item in opportunities))

    def test_aggregation_sorting_and_original_frame(self):
        df = frame([100, 120]).iloc[::-1].copy()
        original = df.copy(deep=True)
        monthly = analisar_meses(df)
        self.assertEqual(monthly["valores_mensais"], {"2026-01": 100, "2026-02": 120})
        self.assertEqual(monthly["registros_por_periodo"], {"2026-01": 5, "2026-02": 5})
        assert_frame_equal(df, original)

    def test_existing_series_are_reused_without_groupby_or_mapping(self):
        df = frame([100, 120, 90])
        df["Lucro"] = df["Faturamento"] / 2
        monthly, performance = analisar_meses(df), analisar_desempenho(df)
        with patch("pandas.DataFrame.groupby", side_effect=AssertionError("groupby repetido")), patch(
                "src.analytics.column_mapper.mapear_colunas", side_effect=AssertionError("mapping repetido")):
            growth = analisar_crescimento(df, monthly, performance)
            gerar_achados_analiticos(temporal=monthly, desempenho=performance, crescimento=growth)

    def test_rounding_cannot_turn_small_valid_values_into_zero_reference(self):
        df = frame([0.004, 0.008])
        df["Lucro"] = df["Faturamento"]
        monthly = analisar_meses(df)
        growth = analisar_crescimento(df)
        self.assertEqual(growth["lucro"]["variacoes"], monthly["variacao_mensal"])
        self.assertEqual(growth["lucro"]["evolucao_total"], 100)
        self.assertEqual(growth["faturamento"]["evolucao_total"], 100)
        summary = gerar_resumo_temporal(monthly, growth, {})
        self.assertEqual(summary["evolucao_metrica"], 100)
        self.assertEqual(summary["comparacao_total"]["previous_value"], 0.004)

    def test_profit_null_period_is_not_imputed_zero_or_tied_to_revenue_coverage(self):
        df = frame([100, 120, 90])
        df["Lucro"] = [10.] * 5 + [None] * 5 + [20.] * 5
        df.loc[10:, "Faturamento"] = None
        result = analisar_crescimento(df)
        self.assertNotIn("2026-02", analisar_desempenho(df)["lucro_mensal"])
        self.assertIsNone(result["lucro"]["variacoes"]["2026-03"])
        self.assertEqual(result["lucro"]["comparacoes"][0]["current_value"], 100)

    def test_summary_preserves_absolute_change_and_cannot_restore_unsafe_percentage(self):
        monthly = analisar_meses(frame([-100, -50], "Lucro"))
        monthly["evolucao_total"] = -50
        summary = gerar_resumo_temporal(monthly, {}, {})
        self.assertIsNone(summary["evolucao_metrica"])
        self.assertEqual(summary["evolucao_variacao_absoluta"], 50)
        self.assertEqual(summary["evolucao_motivo"], "base_negativa")
        self.assertEqual(summary["comparacao_total"]["direction"], "increase")

    def test_cost_increase_is_not_positive_business_insight(self):
        monthly = analisar_meses(frame([100, 150], "Total_custo"))
        messages = gerar_insights({}, monthly, {}, {})
        self.assertTrue(messages)
        self.assertTrue(all(item["tipo"] == "informativo" for item in messages))


class TemporalFindingTests(unittest.TestCase):
    def test_growth_and_decline_have_reproducible_evidence(self):
        for values, rule, delta in [([100, 150], "temporal_growth", 50), ([100, 50], "temporal_decline", -50)]:
            result = findings(values)[0]
            self.assertEqual(result["rule"], rule)
            comparison = result["comparison"]
            self.assertEqual(comparison["absolute_change"], delta)
            self.assertEqual(comparison["current_value"] - comparison["previous_value"], delta)
            self.assertEqual(comparison["percentage_change"], delta)
            self.assertTrue(comparison["continuous"])
            json.dumps(result, allow_nan=False)

    def test_zero_small_and_negative_base_keep_absolute_only(self):
        for values, reason in [([0, 100], "zero_reference"), ([1, 100000], "low_reference_base"),
                               ([-100, -50], "negative_reference"), ([100, -100], "sign_change")]:
            result = findings(values, "Lucro")[0]
            self.assertIsNone(result["comparison"]["percentage_change"])
            self.assertEqual(result["comparison"]["reason"], reason)
            self.assertNotIn("%", result["summary"])
            self.assertNotEqual(result["impact"], "high")

    def test_gap_missing_concept_and_insufficient_series_emit_nothing(self):
        self.assertEqual(findings([100, 50], periods=["2026-01", "2026-03"]), [])
        self.assertEqual(findings([100]), [])
        self.assertEqual(gerar_achados_analiticos(temporal={"valores_mensais": {"2026-01": 1, "2026-02": 100}}), [])
        self.assertEqual(findings([100, 100]), [])

    def test_materiality_does_not_use_only_percentage(self):
        result = findings([10000, 10000, 1, 2])
        self.assertFalse(any(item["period"]["end"] == "2026-04" for item in result))

    def test_impact_confidence_priority(self):
        item = findings([100, 100, 200])[-1]
        self.assertEqual(item["impact"], "high")
        self.assertEqual(item["confidence"], "medium")
        self.assertEqual(item["priority"], "medium")
        small = findings([100, 100, 200], records=1)[-1]
        self.assertEqual(small["impact"], "medium")
        self.assertEqual(small["confidence"], "low")
        self.assertEqual(small["priority"], "low")

    def test_metric_labels_cost_and_conservative_recommendations(self):
        for column, concept in [("Valor_Total", "valor_total"), ("Margem_Bruta", "margem_bruta"), ("Total_custo", "custo")]:
            item = findings([100, 150], column)[0]
            self.assertEqual(item["metric"], concept)
            self.assertNotIn("faturamento", json.dumps(item, ensure_ascii=False).lower())
            self.assertEqual(item["recommendation"], f"Investigar os componentes da variação observada de {item['metric_label']} e conferir a cobertura dos períodos.")

    def test_ids_and_dedup_respect_windows_and_concepts(self):
        a = findings([100, 150])[0]
        b = findings([200, 300])[0]
        self.assertEqual(a["id"], b["id"])
        c = findings([100, 150], periods=["2026-02", "2026-03"])[0]
        self.assertNotEqual(a["id"], c["id"])
        self.assertEqual(len(deduplicar_achados([a, b, c])), 2)

    def test_same_profit_series_not_duplicated_by_producers(self):
        df = frame([100, 150], "Lucro")
        result = gerar_achados_analiticos(temporal=analisar_meses(df), desempenho=analisar_desempenho(df))
        self.assertEqual(len(result), 1)

    def test_snapshot_series_without_coverage_limits_confidence(self):
        temporal = {"metrica": "valor_total", "valores_mensais": {"2026-01": 100, "2026-02": 150}}
        result = gerar_achados_analiticos(temporal=temporal)[0]
        self.assertEqual(result["confidence"], "low")
        self.assertTrue(any("desconhecida" in reason for reason in result["confidence_reasons"]))
