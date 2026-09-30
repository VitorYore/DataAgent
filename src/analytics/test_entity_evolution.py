import json
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from src.analytics.entity_evolution import agregar_entidades_periodo, comparar_entidades
from src.analytics.findings import gerar_achados_analiticos, gerar_achados_entidades, deduplicar_achados, PRIORIDADES
from src.quality.entity_decisions import aplicar_aliases, preparar_revisao, registrar_decisao
from src.quality.entity_resolution import detectar_entidades


def fixture(values=None, kind="cliente", metric="valor_total", repeat=5):
    values = values or {"A": (50, 20), "B": (30, 20), "C": (20, 30)}
    rows = []
    for name, pair in values.items():
        for month, amount in enumerate(pair, 1):
            if amount is not None:
                rows.extend({"Data": pd.Timestamp(2026, month, 15), kind: name, metric: amount / repeat}
                            for _ in range(repeat))
    return pd.DataFrame(rows)


def aggregate(df, kind="cliente", metric="valor_total", report=None):
    roles = {"Data": "data", kind: kind, metric: metric}
    if kind + "_id" in df:
        roles[kind + "_id"] = kind + "_id"
    mapping = {col: {"papel": role, "confianca": 1} for col, role in roles.items() if col in df}
    totals = df.groupby(df.Data.dt.to_period("M"))[metric].sum(min_count=1)
    return agregar_entidades_periodo(df, mapping, {metric: {str(p): float(v) for p, v in totals.items()}}, report)


def findings(df, kind="cliente", metric="valor_total", report=None):
    return gerar_achados_entidades(aggregate(df, kind, metric, report), "test-analysis")


class EntityAggregationTests(unittest.TestCase):
    def test_multiple_records_full_population_and_frame_preserved(self):
        df = fixture({str(i): (100 + i, 30 + i) for i in range(25)})
        original = df.copy(deep=True)
        df.attrs["audit"] = {"keep": [1, 2]}
        original.attrs = df.attrs.copy()
        result = aggregate(df)[0]
        self.assertEqual(len(result["periods"]["2026-01"]["entities"]), 25)
        self.assertEqual(result["periods"]["2026-01"]["entities"]["0"]["value_sum"], 100)
        assert_frame_equal(df, original)

    def test_same_id_different_names_is_one_identity(self):
        df = fixture({"Nome A": (50, 20), "Nome B": (30, 20)})
        df["cliente_id"] = 123
        result = aggregate(df)[0]
        entities = result["periods"]["2026-01"]["entities"]
        self.assertEqual(list(entities), ["123"])
        self.assertEqual(entities["123"]["value_sum"], 80)
        self.assertEqual(entities["123"]["label"], "Nome A")

    def test_same_name_different_ids_remain_separate(self):
        df = fixture({"A": (50, 20), "B": (30, 20)})
        df["cliente_id"] = df.cliente.map({"A": 1, "B": 2})
        df["cliente"] = "Mesmo nome"
        result = findings(df)
        self.assertEqual({f["entity"]["id"] for f in result}, {"1", "2"})
        self.assertEqual(len({f["id"] for f in result}), 2)

    def test_null_ids_do_not_fall_back_to_names(self):
        df = fixture()
        df["cliente_id"] = None
        self.assertEqual(findings(df), [])

    def test_missing_identity_is_in_global_not_fabricated_entity(self):
        df = fixture()
        df.loc[df.cliente == "C", "cliente"] = None
        window = next(comparar_entidades(aggregate(df)[0]))
        self.assertEqual(window["global_comparison"]["absolute_change"], -30)
        self.assertEqual(window["unexplained_by_matched_pairs"], 10)
        self.assertFalse(window["complete_fields"])
        self.assertTrue(all("contributor" not in f["rule"] for f in findings(df)))

    def test_missing_metric_all_null_and_partial_null(self):
        df = fixture()
        df.loc[(df.cliente == "A") & (df.Data.dt.month == 2), "valor_total"] = None
        df.loc[df.index[-1], "valor_total"] = None
        window = next(comparar_entidades(aggregate(df)[0]))
        self.assertEqual(window["absences"]["missing_metric"], 1)
        self.assertNotIn("A", {r["entity"]["value"] for r in window["rows"]})
        self.assertFalse(window["complete_fields"])

    def test_absence_is_not_zero_new_customer_or_churn(self):
        df = fixture({"Sai": (50, None), "Entra": (None, 60), "Fica": (50, 80)})
        window = next(comparar_entidades(aggregate(df)[0]))
        self.assertEqual(window["absences"], {"newly_observed": 1, "not_observed_current": 1, "missing_metric": 0})
        self.assertEqual([r["entity"]["value"] for r in window["rows"]], ["Fica"])
        self.assertEqual(window["unexplained_by_matched_pairs"], 10)
        self.assertEqual({f["entity"]["value"] for f in findings(df)}, {"Fica"})

    def test_gap_single_period_missing_semantics_and_unparsed_date(self):
        df = fixture()
        df.loc[df.Data.dt.month == 2, "Data"] += pd.DateOffset(months=1)
        self.assertEqual(findings(df), [])
        self.assertEqual(findings(df[df.Data.dt.month == 1]), [])
        self.assertEqual(agregar_entidades_periodo(df, {}, {}), [])
        df.Data = df.Data.astype(str)
        self.assertEqual(agregar_entidades_periodo(df, {"Data": {"papel": "data"}}, {"valor_total": {}}), [])

    def test_reconciliation_required_before_reporting_contribution(self):
        item = aggregate(fixture())[0]
        item["global_values"]["2026-01"] = 999
        self.assertEqual(gerar_achados_entidades([item]), [])

    def test_null_dates_reduce_coverage_and_do_not_create_period(self):
        df = fixture()
        extra = df.iloc[:10].copy()
        extra.Data = pd.NaT
        df = pd.concat([df, extra], ignore_index=True)
        window = next(comparar_entidades(aggregate(df)[0]))
        self.assertFalse(window["complete_fields"])
        self.assertEqual(window["coverage"]["2026-01"]["undated_records"], 10)
        self.assertTrue(all(f["confidence"] == "low" for f in findings(df)))

    def test_infinite_values_are_not_valid_metric_observations(self):
        df = fixture()
        df.loc[0, "valor_total"] = float("inf")
        mapping = {"Data": {"papel": "data"}, "cliente": {"papel": "cliente"}, "valor_total": {"papel": "valor_total"}}
        result = agregar_entidades_periodo(df, mapping, {"valor_total": {"2026-01": 90, "2026-02": 70}})
        self.assertEqual(result[0]["periods"]["2026-01"]["valid"], 14)
        json.dumps(gerar_achados_entidades(result), allow_nan=False)

    def test_merge_and_keep_separate_use_existing_analytic_aliases(self):
        df = fixture({"Empresa ABC": (50, 20), "EMPRESA ABC": (30, 20), "Outra": (20, 30)})
        df = df.rename(columns={"cliente": "Cliente", "valor_total": "Valor_Total"})
        original = df.copy(deep=True)
        review = preparar_revisao(detectar_entidades(df), "test", df)
        candidate = review["candidates"][0]
        for decision, expected in (("merge", 2), ("keep_separate", 3)):
            report = registrar_decisao(df, review, {"candidate_id": candidate["candidate_id"], "decision": decision})
            analytic = aplicar_aliases(df, report).rename(columns={"Cliente": "cliente", "Valor_Total": "valor_total"})
            # O relatório continua apontando para o nome físico original.
            for c in report["candidates"]:
                c["column"] = "cliente"
            with patch("src.quality.entity_resolution.detectar_entidades", side_effect=AssertionError("fuzzy repetido")):
                item = aggregate(analytic, report=report)[0]
                result = gerar_achados_entidades([item])
            self.assertEqual(len(item["periods"]["2026-01"]["entities"]), expected)
            if decision == "merge":
                merged = next(f for f in result if f["entity"]["value"] == "Empresa ABC")
                self.assertEqual(merged["comparison"]["previous_value"], 80)
                self.assertEqual(merged["entity"]["identity_source"], "confirmed_alias")
        assert_frame_equal(df, original)


class EntityFindingTests(unittest.TestCase):
    def test_decline_contribution_net_and_gross_compensations(self):
        result = findings(fixture())
        a = next(f for f in result if f["entity"]["value"] == "A")
        e = a["evidence"][0]["value"]
        self.assertEqual(a["rule"], "customer_contributor_decline")
        self.assertEqual(e["global_change"], -30)
        self.assertEqual(e["contribution_denominator"], -30)
        self.assertEqual(e["contribution"], 100)
        self.assertEqual(e["gross_negative_change_matched"], 40)
        self.assertEqual(e["share_of_gross_direction_matched"], 75)
        self.assertEqual(e["unexplained_by_matched_pairs"], 0)
        self.assertEqual(e["previous_share"], 50)
        self.assertAlmostEqual(e["current_share"], 20 / 70 * 100)
        c = next(f for f in result if f["entity"]["value"] == "C")
        self.assertEqual(c["rule"], "customer_growth")
        self.assertIsNone(c["evidence"][0]["value"]["contribution"])

    def test_growth_contribution_and_countermoving_decline(self):
        result = findings(fixture({"A": (20, 50), "B": (20, 30), "C": (30, 20)}))
        self.assertEqual({f["rule"] for f in result}, {"customer_contributor_growth", "customer_decline"})

    def test_net_contribution_can_exceed_one_hundred(self):
        result = findings(fixture({"A": (60, 10), "B": (40, 70)}))
        a = next(f for f in result if f["entity"]["value"] == "A")
        self.assertEqual(a["evidence"][0]["value"]["contribution"], 250)

    def test_flat_global_still_allows_entity_changes_without_contributors(self):
        result = findings(fixture({"A": (60, 30), "B": (40, 70)}))
        self.assertEqual({f["rule"] for f in result}, {"customer_growth", "customer_decline"})

    def test_products_follow_same_rules_in_both_directions(self):
        for values, expected in (({"A": (50, 20), "B": (20, 30)}, {"product_contributor_decline", "product_growth"}),
                                 ({"A": (20, 50), "B": (30, 20)}, {"product_contributor_growth", "product_decline"})):
            self.assertEqual({f["rule"] for f in findings(fixture(values, "produto"), "produto")}, expected)

    def test_small_huge_percentage_does_not_dominate(self):
        result = findings(fixture({"Pequeno": (1, 100), "Grande": (100000, 90000)}))
        self.assertEqual({f["entity"]["value"] for f in result}, {"Grande"})

    def test_zero_small_negative_reference_reuse_temporal_helper(self):
        for pair, reason in (((0, 100), "zero_reference"), ((1, 100000), "low_reference_base"),
                             ((-100, -50), "negative_reference"), ((100, -100), "sign_change")):
            result = findings(fixture({"A": pair}, metric="lucro"), metric="lucro")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["comparison"]["reason"], reason)
            self.assertIsNone(result[0]["comparison"]["percentage_change"])

    def test_many_small_entities_and_output_limit(self):
        self.assertEqual(findings(fixture({str(i): (100, 101) for i in range(1000)}, repeat=1)), [])
        result = findings(fixture({str(i): (100, 50) for i in range(20)}))
        self.assertEqual(len(result), 5)
        self.assertEqual({f["rule"] for f in result}, {"customer_decline"})

    def test_limit_across_many_periods(self):
        df = pd.concat([fixture({str(i): (100, 50) for i in range(20)}).assign(
            Data=lambda d: d.Data + pd.DateOffset(months=offset)) for offset in range(0, 48, 2)], ignore_index=True)
        self.assertLessEqual(len(findings(df)), 100)

    def test_contract_json_evidence_confidence_priority_and_recommendation(self):
        result = findings(fixture())
        json.dumps(result, allow_nan=False)
        a = next(f for f in result if f["entity"]["value"] == "A")
        self.assertEqual((a["impact"], a["confidence"]), ("high", "medium"))
        self.assertEqual(a["priority"], PRIORIDADES[a["impact"]][a["confidence"]])
        self.assertEqual(a["rule_version"], 1)
        self.assertEqual(a["metric_label"], "Valor Total")
        self.assertIn("redução observada", a["summary"])
        self.assertNotIn("faturamento", a["summary"].lower())
        self.assertTrue(a["recommendation"].startswith("Investigar a variação observada"))
        for forbidden in ("insatisfeito", "estoque", "churn", "abandonou", "crescerá", "porque"):
            self.assertNotIn(forbidden, a["summary"] + a["recommendation"])

    def test_sparse_incomplete_period_is_low_confidence(self):
        result = findings(fixture(repeat=1))
        self.assertTrue(all(f["confidence"] == "low" and f["impact"] != "high" for f in result))

    def test_ids_dedup_entities_windows_and_additivity(self):
        aggregates = aggregate(fixture())
        result = gerar_achados_entidades(aggregates, "same")
        self.assertEqual(result, gerar_achados_entidades(aggregates, "same"))
        self.assertEqual(len(deduplicar_achados(result + result)), len(result))
        self.assertEqual(len({f["id"] for f in result}), len(result))
        other = fixture()
        other.Data += pd.DateOffset(months=1)
        self.assertTrue({f["id"] for f in result}.isdisjoint({f["id"] for f in gerar_achados_entidades(aggregate(other), "same")}))
        self.assertEqual(gerar_achados_analiticos(analysis_id="same", entidades=aggregates), result)
        self.assertEqual(gerar_achados_analiticos(), [])

    def test_negative_global_population_has_no_share_claim(self):
        result = findings(fixture({"A": (-50, -100), "B": (100, 150)}, metric="lucro"), metric="lucro")
        self.assertTrue(all(f["evidence"][0]["value"]["previous_share"] is None for f in result))


if __name__ == "__main__":
    unittest.main()
