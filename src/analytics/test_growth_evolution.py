import json
import unittest

import pandas as pd

from src.analytics.growth import avaliar_evolucao_total, calcular_evolucao_total
from src.analytics.insights import gerar_insights
from src.analytics.assisted_mapping import aplicar_mapeamentos
from src.analytics.column_mapper import mapear_colunas
from src.analytics.business import calcular_kpis
from src.analytics.customers import analisar_clientes
from src.reports.executive_summary import gerar_resumo_temporal


class GrowthEvolutionTests(unittest.TestCase):
    def test_explicit_user_mapping_overrides_the_source_header_concept(self):
        source = pd.DataFrame({"Total_custo": [10.0, 25.0]})
        mapped, _ = aplicar_mapeamentos(source, {"Total_custo": "faturamento"})
        self.assertEqual(mapped.columns.tolist(), ["Faturamento"])
        self.assertEqual(mapear_colunas(mapped)["Faturamento"]["papel"], "faturamento")
        self.assertEqual(calcular_kpis(mapped)["faturamento_total"], 35.0)
        self.assertEqual(mapped.attrs["mapeamentos_confirmados"], {"Total_custo": "faturamento"})

    def test_regular_positive_growth_and_decline(self):
        self.assertEqual(calcular_evolucao_total(pd.Series([100, 120])), 20.0)
        self.assertEqual(calcular_evolucao_total(pd.Series([120, 100])), -16.67)
        self.assertEqual(calcular_evolucao_total(pd.Series([100000, 110000])), 10.0)

    def test_zero_and_materially_small_base_are_not_comparable(self):
        self.assertEqual(avaliar_evolucao_total(pd.Series([0, 100]))['motivo'], 'base_zero')
        result = avaliar_evolucao_total(pd.Series([1, 100000]))
        self.assertIsNone(result['variacao_percentual'])
        self.assertEqual(result['motivo'], 'base_muito_baixa')
        self.assertEqual(result['variacao_absoluta'], 99999)

    def test_sign_changes_are_explicit_and_negative_values_keep_direction(self):
        for values in ([-1, 100000], [100000, -1]):
            self.assertEqual(avaliar_evolucao_total(pd.Series(values))['motivo'], 'mudanca_de_sinal')
        self.assertEqual(calcular_evolucao_total(pd.Series([-100, -80])), 20.0)

    def test_customer_negative_insight_has_correct_singular_and_plural(self):
        one = analisar_clientes(pd.DataFrame({'Cliente': ['A'], 'Lucro': [-1]}))
        many = analisar_clientes(pd.DataFrame({'Cliente': ['A', 'B'], 'Lucro': [-1, -2]}))
        self.assertIn('1 cliente apresenta Lucro negativo.', one['insights_clientes'])
        self.assertIn('2 clientes apresentam Lucro negativo.', many['insights_clientes'])

    def test_summary_reports_chronological_values_and_suppresses_extreme_percent(self):
        monthly = {
            "metrica": "lucro", "nome_metrica": "Lucro",
            "valores_mensais": {"2019-06": 38.45, "2020-01": 73306.35, "2020-12": 64252.26},
            "evolucao_total": None, "evolucao_motivo": "base_muito_baixa",
            "evolucao_variacao_absoluta": 64213.81,
            "melhor_mes": {"periodo": "2020-01", "valor": 73306.35},
            "pior_mes": {"periodo": "2019-06", "valor": 38.45},
        }
        result = gerar_resumo_temporal(monthly, {}, {})
        self.assertIsNone(result["evolucao_metrica"])
        self.assertEqual(result["evolucao_motivo"], "base_muito_baixa")
        self.assertEqual(result["evolucao_variacao_absoluta"], 64213.81)
        self.assertEqual(result["periodo_evolucao"]["inicio"], "2019-06")
        self.assertEqual(result["periodo_evolucao"]["fim"], "2020-12")
        self.assertEqual(round((64252.26 - 38.45) / 38.45 * 100, 2), 167006.01)

    def test_insight_preserves_utf8_through_json(self):
        insights = gerar_insights(
            {}, {'melhor_mes': {'periodo': '2020-10', 'valor': 10}, 'metrica': 'lucro', 'nome_metrica': 'Lucro'},
            {}, {},
        )
        message = insights[0]['mensagem']
        expected = 'O per' + chr(237) + 'odo 2020-10'
        self.assertIn(expected, message)
        self.assertIn('per' + chr(237) + 'odo', json.loads(json.dumps(message, ensure_ascii=False)))


if __name__ == '__main__':
    unittest.main()
