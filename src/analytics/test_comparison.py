import json
import unittest

from src.analytics.comparison import comparar_resumos


class ComparisonTests(unittest.TestCase):
    def item(self, identifier, period='2026-01'):
        return {'id': identifier, 'period': {'start': period, 'end': period}}

    def test_only_exact_semantic_metrics_are_compared(self):
        left = {'kpis': {'faturamento_total': 100, 'quantidade_pedidos': 10}}
        right = {'kpis': {'valor_total': 150, 'quantidade_pedidos': 12}}
        result = comparar_resumos(left, right, self.item('a'), self.item('b'))
        self.assertEqual(set(result['metrics']), {'quantidade_pedidos'})
        self.assertEqual(result['metrics']['quantidade_pedidos']['absolute_change'], 2)

    def test_percent_zero_margin_and_direction(self):
        left = {'kpis': {'valor_total': 0, 'margem_bruta_percentual': 30}}
        right = {'kpis': {'valor_total': 10, 'margem_bruta_percentual': 28}}
        result = comparar_resumos(left, right, self.item('a'), self.item('b'))
        self.assertIsNone(result['metrics']['valor_total']['percentage_change'])
        self.assertEqual(result['metrics']['valor_total']['direction'], 'increase')
        self.assertIsNone(result['metrics']['margem_bruta_percentual']['percentage_change'])
        self.assertEqual(result['metrics']['margem_bruta_percentual']['percentage_point_change'], -2)
        self.assertEqual(result['metrics']['margem_bruta_percentual']['direction'], 'decrease')

    def test_periods_and_same_semantic_series(self):
        left = {'kpis': {'valor_total': 100}, 'temporal': {'metrica_principal': 'valor_total', 'nome_metrica_principal': 'Valor Total', 'serie_temporal': [{'periodo': '2026-01', 'metrica_valor': 10}, {'periodo': '2026-02', 'metrica_valor': 12}]}}
        right = {'kpis': {'valor_total': 110}, 'temporal': {'metrica_principal': 'valor_total', 'serie_temporal': [{'periodo': '2026-02', 'metrica_valor': 15}, {'periodo': '2026-03', 'metrica_valor': 16}]}}
        result = comparar_resumos(left, right, self.item('a'), self.item('b'))
        self.assertEqual(result['period_comparability'], 'same_duration')
        self.assertEqual(result['temporal']['shared_periods'], [{'period': '2026-02', 'left': 12, 'right': 15}])

    def test_different_metric_series_are_not_aligned(self):
        left = {'temporal': {'metrica_principal': 'faturamento', 'serie_temporal': [{'periodo': '2026-01', 'metrica_valor': 1}]}}
        right = {'temporal': {'metrica_principal': 'valor_total', 'serie_temporal': [{'periodo': '2026-01', 'metrica_valor': 2}]}}
        result = comparar_resumos(left, right, self.item('a'), self.item('b'))
        self.assertIsNone(result['temporal'])

    def test_customers_use_stable_id_and_ranking_scope(self):
        left = {'clientes': {'ranking_valor_total': [{'cliente': 'Mesmo nome', 'cliente_id': 1, 'valor_total': 20}, {'cliente': 'A', 'cliente_id': 2, 'valor_total': 10}]}}
        right = {'clientes': {'ranking_valor_total': [{'cliente': 'Mesmo nome', 'cliente_id': 1, 'valor_total': 25}, {'cliente': 'A', 'cliente_id': 3, 'valor_total': 9}]}}
        result = comparar_resumos(left, right, self.item('a'), self.item('b'))['dimensions']['clients']
        self.assertEqual(result['common'][0]['id'], '1')
        self.assertEqual(result['common'][0]['absolute_change'], 5)
        self.assertIn({'id': '2', 'label': 'A', 'value': 10}, result['only_left'])
        self.assertIn({'id': '3', 'label': 'A', 'value': 9}, result['only_right'])

    def test_products_are_compared_only_for_both_rankings(self):
        left = {'produtos': {'ranking_produtos': [{'produto': 'P', 'produto_id': 8, 'faturamento': 50}]}}
        right = {'produtos': {'ranking_produtos': [{'produto': 'P', 'produto_id': 8, 'faturamento': 70}]}}
        result = comparar_resumos(left, right, self.item('a'), self.item('b'))
        self.assertEqual(result['dimensions']['products']['common'][0]['absolute_change'], 20)
        json.dumps(result, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
