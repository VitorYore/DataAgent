import copy
import json
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from src.analytics.customers import analisar_clientes
from src.analytics.performance import analisar_desempenho
from src.analytics.findings import (
    PRIORIDADES, deduplicar_achados, gerar_achados_analiticos, identificar_achado,
)
from src.reports.executive_summary import gerar_resumo_executivo


def clientes(values, concept="valor_total", ids=True):
    column = {"valor_total": "Valor_Total", "faturamento": "Faturamento",
              "lucro": "Lucro", "margem_bruta": "Margem_Bruta"}[concept]
    df = pd.DataFrame({"Cliente": [f"Empresa {i}" for i in range(len(values))], column: values})
    if ids:
        df["Cliente_ID"] = range(len(values))
    return analisar_clientes(df)


def evidencia(finding, name):
    return next(item for item in finding["evidence"] if item["name"] == name)


class FindingTests(unittest.TestCase):
    def test_empty_list_and_summary_contract(self):
        self.assertEqual(gerar_achados_analiticos(), [])
        summary = gerar_resumo_executivo({}, {}, {}, {}, {}, {}, [], [])
        self.assertEqual(summary["achados_analiticos"], [])

    def test_required_fields_and_strict_json(self):
        finding = gerar_achados_analiticos(clientes([100] * 10))[0]
        required = {"id", "rule", "rule_version", "type", "title", "summary", "metric",
                    "metric_label", "unit", "scope", "entity", "impact", "confidence",
                    "confidence_reasons", "priority", "evidence", "period", "comparison", "recommendation"}
        self.assertTrue(required <= finding.keys())
        self.assertEqual(finding["rule_version"], 1)
        self.assertIsNone(finding["unit"])
        self.assertTrue(finding["evidence"])
        self.assertEqual(json.loads(json.dumps(finding, allow_nan=False)), finding)

    def test_id_uses_event_not_label_value_or_position(self):
        a = identificar_achado("analysis", "rule", "lucro", "customer", {"id": 0, "value": "A"})
        b = identificar_achado("analysis", "rule", "lucro", "customer", {"id": 0, "value": "B"})
        self.assertEqual(a, b)
        first = gerar_achados_analiticos(clientes([100] * 10), analysis_id="x")[0]
        second = gerar_achados_analiticos(clientes([200] * 10), analysis_id="x")[0]
        self.assertEqual(first["id"], second["id"])
        self.assertNotEqual(first["evidence"], second["evidence"])

    def test_identity_distinguishes_entity_window_reference_and_analysis(self):
        base = ["a", "rule", "lucro", "customer", {"value": "A"}, "2020", {"reference": "2019"}]
        original = identificar_achado(*base)
        for index, value in [(0, "b"), (2, "margem_bruta"), (4, {"value": "B"}),
                             (5, "2021"), (6, {"reference": "2018"})]:
            changed = base.copy()
            changed[index] = value
            self.assertNotEqual(original, identificar_achado(*changed))

    def test_dedup_keeps_one_event_but_separate_entities_and_windows(self):
        finding = gerar_achados_analiticos(clientes([100] * 10))[0]
        findings = [finding, copy.deepcopy(finding)]
        findings[1]["evidence"][0]["source"] = "outra_fonte_do_mesmo_evento"
        for entity, period in [("A", "2020"), ("B", "2020"), ("A", "2021")]:
            item = {**finding, "entity": {"value": entity}, "period": period}
            item["id"] = identificar_achado(None, item["rule"], item["metric"], item["scope"], item["entity"], period)
            findings.append(item)
        self.assertEqual(len(deduplicar_achados(findings)), 4)

    def test_concentration_preserves_concepts_and_reproducible_ratios(self):
        for concept, label in [("valor_total", "Valor Total"), ("faturamento", "Faturamento")]:
            with self.subTest(concept=concept):
                finding = gerar_achados_analiticos(clientes([900] + [10] * 10, concept))[0]
                self.assertEqual(finding["metric"], concept)
                self.assertIn(label, finding["summary"])
                if concept == "valor_total":
                    self.assertNotIn("faturamento", json.dumps(finding, ensure_ascii=False).lower())
                self.assertEqual(finding["impact"], "high")
                self.assertEqual(finding["confidence"], "high")
                self.assertEqual(finding["priority"], "high")
                for name, numerator in [("top1_percentual", 900), ("top5_percentual", 940)]:
                    item = evidencia(finding, name)
                    self.assertEqual(item["numerator"], numerator)
                    self.assertEqual(item["denominator"], 1000)
                    self.assertEqual(item["value"], numerator / 1000 * 100)

    def test_low_medium_and_small_portfolio_concentration(self):
        for values, impact in [([10] * 100, "low"), ([10] * 10, "medium"), ([100, 1], "low")]:
            with self.subTest(impact=impact, population=len(values)):
                item = gerar_achados_analiticos(clientes(values))[0]
                self.assertEqual(item["impact"], impact)
                if len(values) < 10:
                    self.assertEqual(item["confidence"], "low")
                    self.assertIn("2 maiores", item["summary"])

    def test_invalid_denominators_and_insufficient_data(self):
        original = clientes([100] * 10)
        for total in (0, None, -1, float("nan"), float("inf")):
            data = copy.deepcopy(original)
            data["evidencias_metricas"]["valor_total"]["total_metrica"] = total
            self.assertEqual(gerar_achados_analiticos(data), [])
        self.assertEqual(gerar_achados_analiticos({"erro": "sem cliente"}), [])
        original.pop("evidencias_metricas")
        self.assertEqual(gerar_achados_analiticos(original), [])
        self.assertEqual(gerar_achados_analiticos(clientes([None] * 10)), [])
        self.assertEqual(gerar_achados_analiticos(clientes([100, -10])), [])

    def test_text_identity_and_unknown_coverage_limit_confidence(self):
        data = clientes([100] * 10, ids=False)
        self.assertEqual(gerar_achados_analiticos(data)[0]["confidence"], "medium")
        data = clientes([100] * 10)
        del data["evidencias_metricas"]["valor_total"]["registros_validos"]
        self.assertEqual(gerar_achados_analiticos(data)[0]["confidence"], "medium")

    def test_nulls_and_missing_customer_reduce_coverage_not_denominator(self):
        df = pd.DataFrame({"Cliente": ["A", "B", None], "Valor_Total": [100., None, 100.]})
        item = gerar_achados_analiticos(analisar_clientes(df))[0]
        self.assertEqual(evidencia(item, "registros_validos")["value"], 1)
        self.assertEqual(evidencia(item, "populacao")["value"], 1)
        self.assertEqual(evidencia(item, "top1_percentual")["value"], 50)
        self.assertEqual(item["confidence"], "low")

    def test_profit_and_gross_margin_are_distinct(self):
        df = pd.DataFrame({"Cliente": ["A", "B"], "Lucro": [-10., 100.], "Margem_Bruta": [-30., 200.]})
        items = gerar_achados_analiticos(analisar_clientes(df))
        self.assertEqual({item["metric"] for item in items}, {"lucro", "margem_bruta"})
        margin = next(item for item in items if item["metric"] == "margem_bruta")
        self.assertIn("Margem Bruta negativa", margin["summary"])
        self.assertNotIn("lucro", json.dumps(margin, ensure_ascii=False).lower())

    def test_small_isolated_negative_is_low_impact_and_priority(self):
        item = gerar_achados_analiticos(clientes([-5.32] + [1000.] * 99, "lucro"))[0]
        self.assertEqual(item["impact"], "low")
        self.assertEqual(item["priority"], "low")
        self.assertIn("1 cliente apresenta", item["summary"])

    def test_negative_materiality_uses_absolute_population_not_net_total(self):
        item = gerar_achados_analiticos(clientes([-100.] * 5 + [100.] * 5, "lucro"))[0]
        self.assertEqual(item["impact"], "high")
        ratio = evidencia(item, "participacao_magnitude_negativa")
        self.assertEqual(ratio["denominator"], 1000)
        self.assertEqual(ratio["numerator"], 500)
        self.assertEqual(ratio["value"], 50)

    def test_medium_negatives_and_small_population(self):
        for values, impact in [([-100.] * 2 + [100.] * 8, "medium"), ([-100.] * 3, "low")]:
            self.assertEqual(gerar_achados_analiticos(clientes(values, "lucro"))[0]["impact"], impact)

    def test_no_negatives_missing_metric_and_null_population(self):
        self.assertEqual(gerar_achados_analiticos(clientes([0., 10.], "lucro")), [])
        self.assertEqual(gerar_achados_analiticos(clientes([None], "lucro")), [])
        data = clientes([-5., None, 10.], "lucro")
        item = gerar_achados_analiticos(data)[0]
        self.assertEqual(evidencia(item, "populacao")["value"], 2)
        self.assertEqual(evidencia(item, "registros_validos")["value"], 2)

    def test_record_negatives_and_aggregated_customers_are_different_events(self):
        df = pd.DataFrame({"Cliente": ["A", "A", "B"], "Lucro": [-10., 20., -5.]})
        items = gerar_achados_analiticos(analisar_clientes(df), analisar_desempenho(df))
        self.assertEqual({item["scope"] for item in items}, {"customers", "records"})
        for item in items:
            self.assertEqual(evidencia(item, "negativos")["value"], 1 if item["scope"] == "customers" else 2)

    def test_priority_matrix(self):
        self.assertEqual(PRIORIDADES["high"], {"high": "high", "medium": "medium", "low": "medium"})
        self.assertEqual(PRIORIDADES["medium"], {"high": "medium", "medium": "medium", "low": "low"})
        self.assertEqual(set(PRIORIDADES["low"].values()), {"low"})

    def test_recommendations_are_only_investigative(self):
        concentration = gerar_achados_analiticos(clientes([900] + [10] * 10))[0]
        negative = gerar_achados_analiticos(clientes([-10, 20], "lucro"))[0]
        self.assertEqual(concentration["recommendation"], "Monitorar a participação dos principais clientes e investigar possibilidades de diversificação da carteira.")
        self.assertEqual(negative["recommendation"], "Revisar os valores informados de Lucro e investigar os resultados negativos dessa população.")

    def test_generation_preserves_inputs_and_never_recomputes_analytics(self):
        df = pd.DataFrame({"Cliente": ["A", "B"], "Valor_Total": [100., 200.], "Lucro": [-5., 100.]})
        original = df.copy(deep=True)
        customers, performance = analisar_clientes(df), analisar_desempenho(df)
        before = copy.deepcopy((customers, performance))
        with patch("pandas.DataFrame.groupby", side_effect=AssertionError("groupby repetido")), patch(
                "src.analytics.column_mapper.mapear_colunas", side_effect=AssertionError("mapping repetido")):
            gerar_achados_analiticos(customers, performance)
        self.assertEqual((customers, performance), before)
        assert_frame_equal(df, original)

    def test_non_finite_negative_evidence_is_not_emitted(self):
        data = clientes([-10, 20], "lucro")
        data["evidencias_metricas"]["lucro"]["soma_absoluta"] = float("inf")
        self.assertEqual(gerar_achados_analiticos(data), [])
