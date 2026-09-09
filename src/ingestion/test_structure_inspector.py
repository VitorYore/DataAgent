import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import xlwt

from src.ingestion.loader import carregar_dados
from src.ingestion.multi_loader import carregar_multiplas_tabelas
from src.ingestion.structure_inspector import preparar_tabela
from src.quality.validator import gerar_diagnostico


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.root = Path(self.workspace.name)

    def tearDown(self):
        self.workspace.cleanup()

    def excel(self, rows, extension='xlsx', name='tabela'):
        path = self.root / f'{name}.{extension}'
        if extension == 'xlsx':
            pd.DataFrame(rows).to_excel(path, header=False, index=False)
        else:
            book = xlwt.Workbook()
            sheet = book.add_sheet('Dados')
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if value is not None:
                        sheet.write(i, j, value)
            book.save(str(path))
        return path

    def test_csv_normal_preserva_valores_e_tipos(self):
        path = self.root / 'normal.csv'
        path.write_text('Cliente,Valor,Lucro\nALFA,128.7,54.72\nBETA,2,-1\n', encoding='utf-8')
        df = carregar_dados(path)
        pd.testing.assert_frame_equal(df, pd.read_csv(path))
        self.assertEqual(df.attrs['ingestao']['linha_cabecalho'], 1)

    def test_releitura_csv_com_nomes_genericos(self):
        path = self.root / 'generico.csv'
        original = pd.DataFrame({'coluna_1': [20686, 20687], 'coluna_2': [128.7, 90]})
        original.to_csv(path, sep=';', index=False)
        pd.testing.assert_frame_equal(carregar_dados(path), original)

    def test_excel_header_primeira_linha_xlsx_xls(self):
        for extension in ('xlsx', 'xls'):
            path = self.excel([['Cliente', 'Valor'], ['ALFA', 128.7]], extension)
            df = carregar_dados(path)
            pd.testing.assert_frame_equal(df, pd.read_excel(path))
            self.assertTrue(df.attrs['ingestao']['cabecalho_detectado'])

    def test_titulos_antes_header(self):
        for extension in ('xlsx', 'xls'):
            path = self.excel([['Relatório mensal', None, None], ['Emitido pela loja', None, None],
                               ['Cliente', 'Valor', 'Lucro'], ['ALFA', 100, 40]], extension)
            df = carregar_dados(path)
            self.assertEqual(df.attrs['ingestao']['linha_cabecalho'], 3)
            self.assertEqual(list(df.columns), ['Cliente', 'Valor', 'Lucro'])
            self.assertEqual(df.iloc[0].tolist(), ['ALFA', 100, 40])

    def test_sem_header_preserva_primeira_linha(self):
        df = carregar_dados(self.excel([[20686, '2020-01-06', 128.7, 'ALFA'], [20687, '2020-01-07', 90, 'BETA']]))
        self.assertEqual(list(df.columns), ['coluna_1', 'coluna_2', 'coluna_3', 'coluna_4'])
        self.assertEqual(df.iloc[0, 0], 20686)
        self.assertEqual(len(df), 2)
        self.assertFalse(df.attrs['ingestao']['cabecalho_detectado'])

    def test_dados_textuais_nao_viram_header_no_fim_da_amostra(self):
        for quantidade in (2, 25):
            rows = [['ALFA', 'NORTE'], ['BETA', 'SUL']] * quantidade
            df = carregar_dados(self.excel(rows))
            self.assertFalse(df.attrs['ingestao']['cabecalho_detectado'])
            self.assertEqual(df.values.tolist(), rows)
            self.assertEqual(list(df.columns), ['coluna_1', 'coluna_2'])

    def test_colunas_totalmente_vazias(self):
        df = carregar_dados(self.excel([['Cliente', 'Valor', 'Unnamed: 2', 'Vazia'], ['A', 100, None, None], ['B', 20, None, None]]))
        self.assertEqual(list(df.columns), ['Cliente', 'Valor'])
        self.assertEqual(df.attrs['ingestao']['colunas_vazias_removidas'], 2)

    def test_unnamed_com_dados(self):
        df = carregar_dados(self.excel([['Cliente', 'Valor', 'Unnamed: 2'], ['A', 100, 'manter']]))
        self.assertEqual(df['coluna_3'].tolist(), ['manter'])
        self.assertIn({'posicao': 3, 'original': 'Unnamed: 2', 'novo': 'coluna_3'}, df.attrs['ingestao']['colunas_renomeadas'])

    def test_nomes_numericos_duplicados_e_colisoes(self):
        df = preparar_tabela(pd.DataFrame([[1, 2, 3, 4, 5]]), [123, ' Valor ', 'Valor', 'Valor_2', 'coluna_1'], {'linhas_vazias_removidas': 0})
        self.assertEqual(list(df.columns), ['123', 'Valor', 'Valor_3', 'Valor_2', 'coluna_1'])
        self.assertEqual(df.iloc[0].tolist(), [1, 2, 3, 4, 5])

    def test_duplicados_csv_sem_mangling_pandas(self):
        path = self.root / 'duplicados.csv'
        path.write_text('Valor,Valor\n1,2\n', encoding='utf-8')
        df = carregar_dados(path)
        self.assertEqual(list(df.columns), ['Valor', 'Valor_2'])

    def test_linhas_vazias_e_parciais(self):
        df = carregar_dados(self.excel([[None, None], ['Cliente', 'Valor'], ['A', 10], [None, None], ['B', None]]))
        self.assertEqual(len(df), 2)
        self.assertEqual(df.attrs['ingestao']['linhas_vazias_removidas'], 2)
        self.assertTrue(pd.isna(df.iloc[1, 1]))

    def test_coluna_98_porcento_nula_mantida(self):
        rows = [['Cliente', 'Valor', 'Observação']] + [[f'Cliente {i}', i, 'raro' if i == 0 else None] for i in range(50)]
        df = carregar_dados(self.excel(rows))
        self.assertIn('Observação', df)
        self.assertEqual(df.attrs['ingestao']['colunas_muitos_nulos']['Observação'], 98)

    def test_header_desconhecido_por_contraste(self):
        df = carregar_dados(self.excel([['Região', 'Medida'], ['Norte', 3], ['Sul', 4]]))
        self.assertEqual(list(df.columns), ['Região', 'Medida'])

    def test_multitabela_independente_e_diagnostico(self):
        self.excel([['Título', None], ['Cliente', 'Valor'], ['A', 100]], name='primeira')
        self.excel([[20686, 100], [20687, 120]], name='segunda')
        tabelas = carregar_multiplas_tabelas(self.root, estrito=True)
        self.assertEqual(tabelas['primeira'].attrs['ingestao']['linha_cabecalho'], 2)
        self.assertFalse(tabelas['segunda'].attrs['ingestao']['cabecalho_detectado'])
        self.assertIn('ingestao', gerar_diagnostico(tabelas['primeira']))
        self.assertNotIn('ingestao', gerar_diagnostico(pd.DataFrame({'a': [1]})))

    def test_csv_separador_encoding_e_aspas(self):
        for sep, encoding in [(';', 'utf-8-sig'), ('\t', 'latin1'), ('|', 'utf-8')]:
            path = self.root / 'separador.csv'
            original = pd.DataFrame({'Cliente': ['João; Silva', 'B'], 'Valor': [128.7, 2]})
            original.to_csv(path, sep=sep, encoding=encoding, index=False)
            df = carregar_dados(path)
            pd.testing.assert_frame_equal(df, original)
            self.assertEqual(df.attrs['ingestao']['separador'], sep)

    def test_csv_invalido_nao_ignora_linhas(self):
        path = self.root / 'invalido.csv'
        path.write_text('Cliente,Valor\n"sem fechamento', encoding='utf-8')
        with self.assertRaises(Exception):
            carregar_dados(path)

    def test_vendas_tratadas_sem_regressao(self):
        source = Path(__file__).resolve().parents[2] / 'data/processed/vendas_tratadas.csv'
        if not source.exists():
            self.skipTest('Dataset local não disponível')
        pd.testing.assert_frame_equal(carregar_dados(source), pd.read_csv(source, sep=';'))

    def test_pipeline_salva_diagnostico_ingestao(self):
        from main import executar_dataagent
        inputs = self.root / 'inputs'
        inputs.mkdir()
        (inputs / 'vendas.csv').write_text('Cliente;Data;Faturamento;Lucro\nA;2025-01-15;100;40\nB;2025-02-15;200;50\n', encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            summary = executar_dataagent(inputs, self.root / 'output', estrito=True)
        self.assertEqual(summary['kpis']['faturamento_total'], 300)
        report = json.loads((self.root / 'output/reports/diagnostico.json').read_text(encoding='utf-8'))
        self.assertEqual(report['diagnostico']['ingestao']['separador'], ';')


if __name__ == '__main__':
    unittest.main()
