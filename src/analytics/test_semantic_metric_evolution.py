import unittest
import tempfile
from pathlib import Path

import pandas as pd

from src.analytics.assisted_mapping import aplicar_mapeamento_completo, perfilar_colunas
from src.analytics.business import calcular_kpis
from src.analytics.column_mapper import conceito_por_rotulo_cabecalho, mapear_colunas
from src.analytics.customers import analisar_clientes
from src.analytics.temporal import analisar_meses


class SemanticMetricEvolutionTests(unittest.TestCase):
    def test_rotulos_reais_e_aliases_nao_colapsam_conceitos(self):
        labels = [
            'PEDIDO', 'DATA', 'VALOR TOTAL', 'VALOR C/ DESCONTO',
            'FORMA PAGAMENTO', 'CLIENTE', 'MARGEM BRUTA', '% MARGEM BRUTA',
        ]
        expected = [
            'pedido', 'data', 'valor_total', 'valor_com_desconto',
            'forma_pagamento', 'cliente', 'margem_bruta', 'margem_bruta_percentual',
        ]
        self.assertEqual([conceito_por_rotulo_cabecalho(label, labels) for label in labels], expected)
        self.assertEqual(conceito_por_rotulo_cabecalho('VALOR COM DESCONTO'), 'valor_com_desconto')
        self.assertIsNone(conceito_por_rotulo_cabecalho('TOTAL'))
        self.assertIsNone(conceito_por_rotulo_cabecalho('VALOR L\u00cdQUIDO'))
        self.assertEqual(conceito_por_rotulo_cabecalho('VALOR L\u00cdQUIDO', ['VALOR TOTAL', 'VALOR C/ DESCONTO']), 'valor_com_desconto')

    def test_new_metrics_remain_distinct_and_orders_are_unique(self):
        df = pd.DataFrame({
            'Pedido': [10, 10, 11, None, '', 'TOTAL', 'META'],
            'Data': pd.to_datetime(['2018-04-25', '2018-04-25', '2018-04-26', None, None, None, None]),
            'Valor_Total': [100., 200., 300., 1., 2., 900., 1000.],
            'Valor_Com_Desconto': [90., 180., 270., 1., 2., 900., 1000.],
            'Margem_Bruta': [20., 30., 40., 0., 0., 500., 600.],
            'Cliente': ['A', 'A', 'B', None, None, None, None],
            'Forma_Pagamento': ['DINHEIRO', 'CHEQUE E TRANSFER', 'DEBITO', None, None, 'TOTAL', 'META'],
        })
        mapping = mapear_colunas(df)
        self.assertEqual(mapping['Valor_Total']['papel'], 'valor_total')
        self.assertEqual(mapping['Valor_Com_Desconto']['papel'], 'valor_com_desconto')
        self.assertEqual(mapping['Margem_Bruta']['papel'], 'margem_bruta')
        self.assertNotIn('custo_total', calcular_kpis(df))
        self.assertNotIn('lucro_total', calcular_kpis(df))
        self.assertNotIn('faturamento_total', calcular_kpis(df))
        kpis = calcular_kpis(df)
        self.assertEqual(kpis['valor_total'], 2503.0)
        self.assertEqual(kpis['valor_com_desconto'], 2443.0)
        self.assertEqual(kpis['margem_bruta'], 1190.0)
        self.assertEqual(kpis['quantidade_pedidos'], 2)
        self.assertEqual(kpis['quantidade_registros'], len(df))

    def test_percentual_nao_e_agregado_sem_base_comprovada(self):
        df = pd.DataFrame({
            'Margem_Bruta': [20., 30.],
            'Margem_Bruta_Percentual': [20., 60.],
            'Valor_Total': [100., 100.],
            'Valor_Com_Desconto': [50., 300.],
        })
        self.assertNotIn('margem_bruta_percentual', calcular_kpis(df))

    def test_formula_comprova_base_e_calcula_percentual_agregado_ponderado(self):
        df = pd.DataFrame({
            'Margem_Bruta': [20., 30.],
            'Margem_Bruta_Percentual': [20., 10.],
            'Valor_Total': [100., 100.],
            'Valor_Com_Desconto': [100., 300.],
        })
        columns = [
            {'posicao': 3, 'rotulo': 'VALOR TOTAL', 'mapeamento_permitido': True, 'confianca': 96},
            {'posicao': 4, 'rotulo': 'VALOR C/ DESCONTO', 'mapeamento_permitido': True, 'confianca': 96},
            {'posicao': 7, 'rotulo': 'MARGEM BRUTA', 'mapeamento_permitido': True, 'confianca': 96},
            {'posicao': 8, 'rotulo': '% MARGEM BRUTA', 'mapeamento_permitido': True, 'confianca': 96},
        ]
        df.attrs['ingestao'] = {'normalizacao': {
            'evidencias_cabecalho_tardio': [{'validado': True, 'colunas': columns}],
            'blocos': [{'linhas_origem': [2, 3]}],
            'evidencias_excel': {'formulas': [
                {'linha': 2, 'coluna': 8, 'formula': '=G2/D2'},
                {'linha': 3, 'coluna': 8, 'formula': '=G3/D3'},
            ]},
        }}
        kpis = calcular_kpis(df)
        self.assertEqual(kpis['margem_bruta_percentual'], 12.5)
        self.assertEqual(kpis['margem_bruta_percentual_linhas_base'], 2)

    def test_percentual_nao_agrega_blocos_com_bases_de_formula_diferentes(self):
        from src.analytics.business import _margem_bruta_percentual_por_formulas
        frame = pd.DataFrame({
            'Margem_Bruta': [20., 30.],
            'Valor_Total': [100., 100.],
            'Valor_Com_Desconto': [100., 300.],
        })
        columns = [
            {'posicao': 3, 'rotulo': 'VALOR TOTAL', 'mapeamento_permitido': True},
            {'posicao': 4, 'rotulo': 'VALOR C/ DESCONTO', 'mapeamento_permitido': True},
            {'posicao': 7, 'rotulo': 'MARGEM BRUTA', 'mapeamento_permitido': True},
            {'posicao': 8, 'rotulo': '% MARGEM BRUTA', 'mapeamento_permitido': True},
        ]
        frame.attrs['ingestao'] = {'normalizacao': {
            'evidencias_cabecalho_tardio': [{'validado': True, 'colunas': columns}],
            'blocos': [{'linhas_origem': [2, 3]}],
            'evidencias_excel': {'formulas': [
                {'linha': 2, 'coluna': 8, 'formula': '=G2/C2'},
                {'linha': 3, 'coluna': 8, 'formula': '=G3/D3'},
            ]},
        }}
        mapped = {'gross': {'papel': 'margem_bruta'}, 'base_a': {'papel': 'valor_total'}, 'base_b': {'papel': 'valor_com_desconto'}}
        frame = frame.rename(columns={'Margem_Bruta': 'gross', 'Valor_Total': 'base_a', 'Valor_Com_Desconto': 'base_b'})
        frame.attrs['mapeamentos_confirmados'] = {'coluna_4': 'valor_com_desconto'}
        self.assertIsNone(_margem_bruta_percentual_por_formulas(frame, mapped))

    def test_temporal_aceita_metricas_sem_faturamento(self):
        dates = pd.to_datetime(['2020-01-02', '2020-01-15', '2020-02-02', '2020-02-20'])
        for column, expected in [('Valor_Total', 'valor_total'), ('Valor_Com_Desconto', 'valor_com_desconto'), ('Margem_Bruta', 'margem_bruta')]:
            df = pd.DataFrame({'Data': dates, column: [10., 20., 30., 40.]})
            analysis = analisar_meses(df)
            self.assertEqual(analysis['metrica'], expected)
            self.assertEqual(len(analysis['valores_mensais']), 2)
            summary_series = analysis['valores_mensais']
            self.assertEqual(summary_series['2020-01'], 30.0)

    def test_data_detectada_por_conteudo_chega_datetime_ao_analytics(self):
        df = pd.DataFrame({'coluna_1': ['25/04/2018', '26/04/2018', '27/04/2018'], 'coluna_2': [10., 20., 30.]})
        df.attrs['ingestao'] = {'normalizacao': {'estrutura_detectada': 'relatorio_operacional'}}
        detected, _, automatic = perfilar_colunas(df)
        self.assertEqual(automatic['coluna_1'], 'data')
        mapped, _ = aplicar_mapeamento_completo(df, automatic, {'coluna_2': 'valor_total'})
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(mapped['Data']))
        self.assertEqual(analisar_meses(mapped)['metrica'], 'valor_total')

    def test_temporal_parse_dates_from_text_without_mutating_source(self):
        dates = ['25/04/2018', '26/04/2018', '25/05/2018']
        frame = pd.DataFrame({'Data': dates, 'Valor_Total': [10.0, 20.0, 30.0]})
        original = frame['Data'].copy()
        result = analisar_meses(frame)
        self.assertEqual(result['valores_mensais'], {'2018-04': 30.0, '2018-05': 30.0})
        pd.testing.assert_series_equal(frame['Data'], original)

    def test_insight_temporal_usa_metric_name_without_requiring_revenue_key(self):
        from src.analytics.insights import gerar_insights
        monthly = {
            'metrica': 'valor_total', 'nome_metrica': 'Valor Total',
            'melhor_mes': {'periodo': '2018-04', 'valor': 3400.0},
        }
        result = gerar_insights({}, monthly, {}, {}, {}, {}, {}, [])
        self.assertIn('maior valor de Valor Total', result[0]['mensagem'])
        self.assertEqual(result[0]['metrica'], 'valor_total')

    def test_cliente_usa_valor_total_sem_inventar_faturamento(self):
        df = pd.DataFrame({'Cliente': ['A', 'A', 'B'], 'Valor_Total': [10., 20., 25.]})
        result = analisar_clientes(df)
        self.assertEqual(result['maior_valor_total']['cliente'], 'A')
        self.assertEqual(result['maior_valor_total']['valor_total'], 30.)
        self.assertNotIn('maior_faturamento', result)
        self.assertEqual(result['ranking_faturamento'], [])


    def test_mapeamento_preserva_origem_de_cabecalho_tardio(self):
        from main import executar_pipeline_analitico

        frame = pd.DataFrame({'coluna_1': [100.0, 200.0], 'coluna_2': ['a', 'b']})
        frame.attrs['ingestao'] = {'normalizacao': {
            'evidencias_cabecalho_tardio': [{
                'validado': True,
                'origem': 'cabecalho_posterior',
                'colunas': [
                    {'posicao': 1, 'mapeamento_permitido': True, 'confianca': 96},
                    {'posicao': 2, 'mapeamento_permitido': True, 'confianca': 96},
                ],
            }],
        }}
        with tempfile.TemporaryDirectory() as output:
            summary = executar_pipeline_analitico(
                frame, origem='fixture', diretorio_saida=Path(output),
                semantic_mappings={}, automatic_mappings={'coluna_1': 'valor_total'},
            )
        origins = summary['dados']['mapeamento_semantico']['origens']
        self.assertEqual(origins['coluna_1'], {'origem': 'cabecalho_posterior', 'confianca': 0.96})
        self.assertNotIn('coluna_2', origins)


if __name__ == '__main__':
    unittest.main()
