import copy
import json
import random
import unittest

from src.analytics.finding_selection import selecionar_achados_principais, familia_achado, materialidade_achado
from src.analytics.findings import gerar_achados_analiticos
from src.analytics.test_entity_evolution import fixture, aggregate
from src.analytics.temporal import analisar_meses
from src.analytics.customers import analisar_clientes


def finding(i, family="clientes", priority="medium", impact="medium", confidence="medium", magnitude=0.3):
    rule, scope = {"clientes": ("customer_decline", "customers"), "produtos": ("product_decline", "products"),
                   "temporal": ("temporal_decline", "temporal"),
                   "concentracao": ("customer_concentration", "customers"),
                   "resultados_negativos": ("negative_results", "records")}[family]
    return {"id": str(i), "rule": rule, "rule_version": 1, "type": rule, "scope": scope,
            "metric": "valor_total", "metric_label": "Valor Total", "unit": None,
            "entity": {"id": str(i), "label": str(i)} if family in ("clientes", "produtos") else None,
            "period": {"start": "2026-01", "end": f"2026-{i}"}, "comparison": None,
            "impact": impact, "confidence": confidence, "priority": priority,
            "confidence_reasons": ["Fixture de seleção"], "title": "Observação", "summary": "Resumo",
            "evidence": [{"name": "materialidade_absoluta", "value": magnitude}],
            "recommendation": "Investigar a variação observada."}


class FindingSelectionTests(unittest.TestCase):
    def test_empty_one_and_less_than_limit(self):
        self.assertEqual(selecionar_achados_principais([]), [])
        for size in (1, 3):
            self.assertEqual(len(selecionar_achados_principais([finding(i) for i in range(size)])), size)

    def test_limit_and_many_from_each_family(self):
        for family in ("clientes", "produtos", "temporal"):
            data = [finding(i, family) for i in range(100)]
            self.assertEqual(len(selecionar_achados_principais(data)), 8)
            self.assertEqual(len(selecionar_achados_principais(data, 100)), 8)
            self.assertEqual(selecionar_achados_principais(data, 0), [])

    def test_diversity_with_equal_rank_does_not_promote_low_concentration(self):
        data = ([finding(i, magnitude=0.9) for i in range(8)] +
                [finding(i+10, "temporal", magnitude=0.4) for i in range(3)] +
                [finding(i+20, "produtos", magnitude=0.2) for i in range(2)] +
                [finding(30, "concentracao", "low", "low", "low")])
        result = selecionar_achados_principais(data)
        self.assertEqual({familia_achado(f) for f in result[:3]}, {"clientes", "temporal", "produtos"})
        self.assertNotIn("30", {f["id"] for f in result})
        self.assertLess(sum(familia_achado(f) == "clientes" for f in result), 8)

    def test_priority_before_diversity_and_materiality(self):
        data = [finding(i, priority="high", impact="high", confidence="high", magnitude=.1) for i in range(8)]
        data.append(finding(20, "temporal", magnitude=100))
        self.assertTrue(all(f["priority"] == "high" for f in selecionar_achados_principais(data)))

    def test_concentration_and_negatives_join_diversity_when_material(self):
        data = [finding(i, "clientes") for i in range(10)]
        data += [finding(20, "concentracao"), finding(21, "resultados_negativos")]
        result = selecionar_achados_principais(data)
        self.assertEqual({familia_achado(f) for f in result[:3]}, {"clientes", "concentracao", "resultados_negativos"})

    def test_lesser_confidence_is_not_promoted_to_fill_family(self):
        data = [finding(i, "temporal") for i in range(10)]
        data += [finding(20, "produtos", priority="low", confidence="low", magnitude=10)]
        self.assertEqual({familia_achado(f) for f in selecionar_achados_principais(data)}, {"temporal"})

    def test_impact_then_confidence_within_priority(self):
        data = [finding(1, impact="medium", confidence="high", magnitude=5),
                finding(2, impact="high", confidence="medium", magnitude=.1),
                finding(3, impact="high", confidence="high", magnitude=.1)]
        self.assertEqual([f["id"] for f in selecionar_achados_principais(data)], ["3", "2", "1"])

    def test_materiality_and_unknown_evidence(self):
        data = [finding(1, magnitude=.1), finding(2, magnitude=.9), finding(3)]
        data[-1]["evidence"] = []
        self.assertEqual([f["id"] for f in selecionar_achados_principais(data)], ["2", "1", "3"])
        self.assertIsNone(materialidade_achado(data[-1]))

    def test_reuse_entity_concentration_and_negative_ratios(self):
        item = finding(1)
        for evidence, expected in (({"name": "top5_percentual", "value": 22.28}, .2228),
                                   ({"name": "participacao_magnitude_negativa", "value": 5}, .05),
                                   ({"name": "evolucao_entidade", "value": {"materiality": {"numerator": 20, "denominator": 100}}}, .2)):
            item["evidence"] = [evidence]
            self.assertAlmostEqual(materialidade_achado(item), expected)

    def test_low_impact_not_used_as_padding_and_only_low_can_be_short(self):
        low = [finding(i, "concentracao", "low", "low") for i in range(10)]
        self.assertEqual(len(selecionar_achados_principais(low)), 2)
        self.assertEqual([f["id"] for f in selecionar_achados_principais(low+[finding(99)])], ["99"])

    def test_low_confidence_does_not_dominate_but_can_appear(self):
        low = [finding(i, priority="low", confidence="low") for i in range(10)]
        result = selecionar_achados_principais([finding(90)] + low)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "90")
        self.assertEqual(result[1]["confidence"], "low")
        self.assertEqual(len(selecionar_achados_principais(low)), 8)

    def test_deterministic_for_shuffled_input_and_duplicate_payloads(self):
        data = [finding(i, ["clientes", "produtos", "temporal"][i % 3], magnitude=i / 100) for i in range(30)]
        duplicate = copy.deepcopy(data[0])
        duplicate["summary"] = "Outro texto do mesmo ID"
        data.extend([duplicate, copy.deepcopy(data[0])])
        expected = selecionar_achados_principais(data)
        for seed in range(5):
            shuffled = list(data)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(selecionar_achados_principais(shuffled), expected)

    def test_individual_contributor_overlap_but_global_remains(self):
        individual = finding(1)
        contributor = {**individual, "id": "contributor", "rule": "customer_contributor_decline"}
        temporal = {**finding(2, "temporal"), "period": individual["period"]}
        result = selecionar_achados_principais([individual, contributor, temporal])
        self.assertEqual({f["id"] for f in result}, {"contributor", "2"})

    def test_distinct_entities_windows_metrics_and_references_are_not_duplicates(self):
        one = finding(1)
        two = {**one, "id": "2", "entity": {"id": "2"}}
        three = {**one, "id": "3", "period": {"start": "2026-02", "end": "2026-03"}}
        four = {**one, "id": "4", "metric": "lucro"}
        five = {**one, "id": "5", "comparison": {"reference": "outra"}}
        self.assertEqual(len(selecionar_achados_principais([one, two, three, four, five])), 5)

    def test_repeated_recommendation_has_reference_without_erasing_original(self):
        data = [finding(i) for i in range(3)]
        data[-1]["recommendation"] = None
        result = selecionar_achados_principais(data)
        self.assertTrue(result[0]["show_recommendation"])
        self.assertFalse(result[1]["show_recommendation"])
        self.assertEqual(result[1]["recommendation_reference"], result[0]["id"])
        self.assertEqual(result[1]["recommendation"], data[1]["recommendation"])
        self.assertFalse(result[2]["show_recommendation"])

    def test_original_findings_evidence_and_contract_are_preserved(self):
        data = [finding(i) for i in range(10)]
        original = copy.deepcopy(data)
        result = selecionar_achados_principais(data)
        self.assertEqual(data, original)
        for selected in result:
            source = next(f for f in data if f["id"] == selected["id"])
            self.assertEqual({k: selected[k] for k in source}, source)
            self.assertEqual(selected["selection_reason"]["family"], familia_achado(source))
        json.dumps(result, allow_nan=False)

    def test_existing_generated_recommendations_are_conservative(self):
        df = fixture()
        result = gerar_achados_analiticos(entidades=aggregate(df))
        temporal_df = df.rename(columns={"cliente": "Cliente", "valor_total": "Valor_Total"})
        result += gerar_achados_analiticos(clientes=analisar_clientes(temporal_df), temporal=analisar_meses(temporal_df))
        result += gerar_achados_analiticos(desempenho={"evidencias_negativos": {
            "negativos": 2, "populacao": 20, "soma_negativos": -20, "soma_absoluta": 100,
            "registros": 20, "registros_validos": 20}})
        for f in result:
            recommendation = f["recommendation"]
            if recommendation:
                self.assertTrue(recommendation.startswith(("Investigar", "Monitorar", "Revisar")))
                for forbidden in ("porque", "insatisfeito", "crescerá", "aumentar estoque", "abandonou"):
                    self.assertNotIn(forbidden, recommendation.casefold())


if __name__ == "__main__":
    unittest.main()
