import unittest
import json
import pandas as pd
from src.ingestion.report_normalizer import normalizar_relatorio, StructuralReviewRequired


def linhas(n=100, offset=0, data=True):
    return [[i + offset, '2025-01-15' if data else 'Produto', float(i + 0.25), 'Texto', float(i + 0.5)] for i in range(n)]


class RepetitionTests(unittest.TestCase):
    def run_report(self, rows, formulas=None):
        return normalizar_relatorio(pd.DataFrame(rows), evidencias={'formulas': formulas or []})

    def test_sem_header(self):
        r = self.run_report([['JAN/2021'], *linhas(), ['TOTAL', None, 1000]])
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertEqual(len(r['blocos'][0]), 100)
        self.assertTrue(all(c.startswith('coluna_') for c in r['blocos'][0]))

    def test_headerless_transacoes_com_resumos_sao_aceitas(self):
        rows = [['Jan/2025'], *linhas(100), ['TOTAL', None, 1000, None, None],
                ['META', None, 1200, None, None], ['Obs. fechamento', None, None, None, None]]
        result = self.run_report(rows)
        self.assertFalse(result['metadados']['revisao_necessaria'])
        self.assertIn(result['metadados']['status'], ('accepted', 'partial'))
        self.assertEqual(result['metadados']['registros_extraidos'], 100)
        self.assertEqual(result['metadados']['linhas_resumo'], 2)

    def test_formula_agregada_quebrada_e_resumo_auditado(self):
        rows = [['Jan/2025'], *linhas(100), [None, None, '=SUM(#REF!)', None, None]]
        formulas = [{'linha': 102, 'coluna': 3, 'formula': '=SUM(#REF!)', 'sem_cache': True}]
        result = self.run_report(rows, formulas)
        self.assertFalse(result['metadados']['revisao_necessaria'])
        self.assertEqual(result['metadados']['registros_extraidos'], 100)
        self.assertEqual(result['metadados']['linhas_resumo'], 1)
        self.assertIn(result['metadados']['auditoria_linhas'][-1]['tipo'], ('total', 'resumo'))

    def test_blocos_curto_repetidos_sao_agregados_pela_assinatura(self):
        rows = []
        for month in range(20):
            rows.extend([['JAN/2025'], *linhas(4, offset=month * 4), ['TOTAL', None, 10, None, None]])
        result = self.run_report(rows)
        self.assertFalse(result['metadados']['revisao_necessaria'])
        self.assertEqual(result['metadados']['registros_extraidos'], 80)
        self.assertEqual(result['metadados']['confidence_transaction_structure'], 100.0)

    def test_com_header(self):
        r = self.run_report([['ID', 'Data', 'Valor', 'Nome', 'Outro'], ['Janeiro'], *linhas()])
        self.assertEqual(len(r['blocos'][0]), 100)
        self.assertIn('Valor', r['blocos'][0])

    def test_mensais(self):
        r = self.run_report([['APRIL'], *linhas(), ['TOTAL'], ['MAI/2025'], *linhas(offset=100)])
        self.assertEqual(r['metadados']['linhas_periodo'], 2)
        self.assertEqual(len(r['metadados']['blocos_transacionais']), 2)

    def test_trimestrais(self):
        r = self.run_report([['1º TRIMESTRE 2025'], *linhas(), ['Q2/2025'], *linhas(offset=100)])
        self.assertEqual(r['metadados']['linhas_periodo'], 2)

    def test_resumos_intercalados(self):
        r = self.run_report([['Janeiro'], *linhas(), ['META', 100], ['23 DIAS ÚTEIS'], ['SALDO', 25], ['Março'], *linhas(offset=100)])
        self.assertEqual(r['metadados']['registros_extraidos'], 200)
        self.assertEqual(r['metadados']['linhas_resumo'], 3)

    def test_ordens_e_quantidades(self):
        for ordem in ([4, 3, 0, 2, 1], [2, 0, 4, 3, 1]):
            rows = [[r[c] for c in ordem] + [None, 'Extra'] for r in linhas()]
            r = self.run_report([['Janeiro'], *rows])
            self.assertEqual(r['metadados']['registros_extraidos'], 100)
            self.assertIn(ordem.index(0) + 1, r['metadados']['posicoes_identificadores_provaveis'])

    def test_sem_data(self):
        r = self.run_report([['Janeiro'], *linhas(data=False)])
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertEqual(r['metadados']['registros_extraidos'], 100)

    def test_blocos_compativeis_semantica_neutra(self):
        r = self.run_report([['Janeiro'], *linhas(), ['ID', 'Data', 'Valor', 'Nome', 'Outro'], ['Março'], *linhas(offset=100)])
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertEqual(len(r['blocos']), 1)
        self.assertEqual(len(r['blocos'][0]), 200)
        self.assertTrue(all(c.startswith('coluna_') for c in r['blocos'][0]))

    def test_blocos_incompativeis(self):
        others = [[r[1], r[3], r[0], r[4], r[2]] for r in linhas()]
        r = self.run_report([['Janeiro'], *linhas(), ['Março'], *others])
        self.assertTrue(r['metadados']['revisao_necessaria'])

    def test_ambiguo_continua_bloqueado(self):
        r = self.run_report([['Janeiro'], ['Texto inexplicável'], [1, 2], ['X', 'Y', 'Z']])
        self.assertTrue(r['metadados']['revisao_necessaria'])

    def test_tabela_normal_preservada(self):
        r = self.run_report([['ID', 'Data', 'Valor', 'Nome', 'Outro'], *linhas()])
        self.assertFalse(r['aplicado'])

    def test_moeda_separada(self):
        rows = [[r[0], r[1], 'Pessoa', '£', f'{r[2]:.2f}'] for r in linhas()]
        r = self.run_report([['January'], *rows])
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertEqual(len(r['blocos'][0].columns), 4)

    def test_total_formula_sem_rotulo(self):
        rows = [['Janeiro'], *linhas(), [None, None, 10000, None, 5000]]
        r = self.run_report(rows, [{'linha': 102, 'coluna': 3, 'formula': '=SUM(C2:C101)', 'sem_cache': False}])
        self.assertEqual(r['metadados']['registros_extraidos'], 100)
        self.assertEqual(r['metadados']['linhas_resumo'], 1)

    def test_formula_opcional_indisponivel(self):
        rows = [['Janeiro'], *linhas()]
        rows[50][4] = '=C51/0'
        formulas = [{'linha': i+2, 'coluna': 5, 'formula': f'=C{i+2}/2', 'sem_cache': i == 49} for i in range(100)]
        r = self.run_report(rows, formulas)
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertTrue(pd.isna(r['blocos'][0].iloc[49, 4]))
        self.assertEqual(len(r['metadados']['formulas_indisponiveis']), 1)

    def test_formulas_indisponiveis_em_massa_bloqueiam(self):
        rows = [['Janeiro'], *linhas()]
        for row in rows[1:]: row[4] = '=C2/0'
        formulas = [{'linha': i+2, 'coluna': 5, 'formula': '=C2/0', 'sem_cache': True} for i in range(100)]
        self.assertTrue(self.run_report(rows, formulas)['metadados']['revisao_necessaria'])

    def test_residual_esparso_auditado(self):
        r = self.run_report([['Janeiro'], *linhas(500), ['Texto complementar não padronizado']])
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertTrue(r['metadados']['residuais_preservados'])
        self.assertEqual(r['metadados']['linhas_desconhecidas'], 1)
        self.assertEqual(r['metadados']['auditoria_linhas'][-1]['valores'][0], 'Texto complementar não padronizado')

    def test_residual_com_id_fica_auditado_em_estado_parcial(self):
        r = self.run_report([['Janeiro'], *linhas(500), [501, None, None, 'Registro incompleto']])
        self.assertFalse(r['metadados']['revisao_necessaria'])
        self.assertEqual(r['metadados']['status'], 'partial')
        self.assertEqual(r['metadados']['linhas_desconhecidas'], 1)
        self.assertEqual(r['metadados']['auditoria_linhas'][-1]['valores'], [501, None, None, 'Registro incompleto', None])

    def test_vazios_nao_inflam_compatibilidade(self):
        rows = [['Janeiro'], *linhas(), ['Março'], *[[r[1],r[3],r[0],r[4],r[2]] for r in linhas()]]
        r = self.run_report([row + [None]*40 for row in rows])
        self.assertTrue(r['metadados']['revisao_necessaria'])

    def test_detalhe_422_seguro(self):
        r = self.run_report([['Janeiro'], ['desconhecido']])
        detail = StructuralReviewRequired({'abas': {'A': r['metadados']}}).detalhe_publico()
        self.assertIn('motivo', detail)
        self.assertNotIn('C:', json.dumps(detail))
        self.assertEqual(detail['diagnostico'], 'diagnostico_estrutural.json')


if __name__ == '__main__': unittest.main()
