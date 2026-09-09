import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from src.quality.validator import gerar_diagnostico
from src.quality.issues import gerar_problemas
from src.reports.data_quality import gerar_qualidade_dados
from src.ingestion.loader import carregar_dados
from main import executar_dataagent, executar_pipeline_analitico


class DataQualityTests(unittest.TestCase):
    def quality(self, df):
        d = gerar_diagnostico(df)
        return gerar_qualidade_dados(d, gerar_problemas(df, d), [], [{'nome': 'teste', 'linhas': len(df), 'colunas': len(df.columns)}])

    def test_sem_problemas(self):
        q = self.quality(pd.DataFrame({'valor': [1, 2]}))
        self.assertEqual(q['score_qualidade'], 100)
        self.assertEqual(q['classificacao_qualidade'], 'excelente')
        self.assertEqual(q['problemas'], [])
        self.assertEqual(q['transformacoes'], [])

    def test_nulos(self):
        q = self.quality(pd.DataFrame({'valor': [1, None]}))
        self.assertEqual(q['total_valores_nulos'], 1)
        self.assertEqual(q['percentual_nulos_geral'], 50)
        self.assertEqual(q['score_qualidade'], 70)
        self.assertEqual(q['problemas'][0]['nivel'], 'baixa')

    def test_duplicadas(self):
        q = self.quality(pd.DataFrame({'valor': [1, 1]}))
        self.assertEqual(q['linhas_duplicadas'], 1)
        self.assertEqual(q['score_qualidade'], 75)

    def test_sem_header_e_colunas_removidas(self):
        df = pd.DataFrame({'coluna_1': [1, 2]})
        df.attrs['ingestao'] = {'cabecalho_detectado': False, 'colunas_vazias_removidas': 3}
        q = self.quality(df)
        self.assertEqual(q['score_qualidade'], 87)
        self.assertEqual(q['ingestao'], df.attrs['ingestao'])

    def test_logs_preservados_e_problemas_ordenados(self):
        d = gerar_diagnostico(pd.DataFrame({'a': [1]}))
        log = {'timestamp': 'ignorado', 'tipo_transformacao': 'tipo', 'coluna': 'Data', 'antes': 'str', 'depois': 'datetime', 'detalhes': 'Convertida.'}
        q = gerar_qualidade_dados(d, [{'mensagem': 'B', 'severidade': 'baixa'}, {'mensagem': 'A', 'severidade': 'alta'}], [log], [])
        self.assertEqual(q['problemas'][0]['mensagem'], 'A')
        self.assertEqual(q['transformacoes'][0]['descricao'], log['detalhes'])
        self.assertEqual(q['transformacoes'][0]['antes'], 'str')
        self.assertNotIn('timestamp', q['transformacoes'][0])

    def test_tabela_vazia_sem_score_inventado(self):
        q = self.quality(pd.DataFrame({'valor': pd.Series(dtype=float)}))
        self.assertIsNone(q['percentual_nulos_geral'])
        self.assertIsNone(q['score_qualidade'])

    def test_multitabela_pipeline(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            base = Path(directory)
            inputs = base / 'input'
            inputs.mkdir()
            for name in ('Historico_Vendas.csv', 'Produtos.csv', 'Clientes.csv'):
                pd.read_csv(root / 'data/samples' / name).head(1000).to_csv(inputs / name, index=False)
            summary = executar_dataagent(inputs, base / 'output', estrito=True)
            q = summary['dados']
            self.assertEqual(q['quantidade_arquivos'], 3)
            self.assertEqual(len(q['ingestao']), 3)
            self.assertEqual({f['nome'] for f in q['arquivos']}, {'Historico_Vendas.csv', 'Produtos.csv', 'Clientes.csv'})
            self.assertTrue(all(f['linhas'] == 1000 for f in q['arquivos']))
            json.dumps(summary, allow_nan=False)

    def test_csv_real(self):
        root = Path(__file__).resolve().parents[2]
        path = root / 'data/processed/vendas_tratadas.csv'
        if not path.exists():
            self.skipTest('CSV local ausente')
        df = carregar_dados(path)
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            summary = executar_pipeline_analitico(df, path.name, Path(directory))
        q = summary['dados']
        self.assertEqual(q['quantidade_linhas'], len(df))
        self.assertEqual(q['total_valores_nulos'], int(df.isna().sum().sum()))
        self.assertTrue(q['ingestao']['cabecalho_detectado'])
        self.assertEqual(q['arquivos'][0]['nome'], path.name)
        self.assertTrue(q['transformacoes'])


if __name__ == '__main__':
    unittest.main()
