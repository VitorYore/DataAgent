import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from api.app import create_app
from main import executar_dataagent

CSV = b'Cliente,Data,Faturamento,Lucro\nA,2025-01-15,100,40\nB,2025-02-15,200,50\n'


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.client = TestClient(create_app(self.root / 'reports/resumo_executivo.json', self.root / 'uploads'))
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()

    def tearDown(self):
        self.stdout.__exit__(None, None, None)
        self.client.close()
        self.temp.cleanup()

    def post(self, origin='http://localhost:5174'):
        return self.client.post('/api/analysis', headers={'Origin': origin}, files=[('files', ('vendas.csv', CSV))])

    def test_origens_locais_post_get_preflight(self):
        for host in ('localhost', '127.0.0.1'):
            for port in (5173, 5174):
                origin = f'http://{host}:{port}'
                response = self.post(origin)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['access-control-allow-origin'], origin)
                summary = response.json()['summary']
                json.dumps(summary, allow_nan=False)
                self.assertTrue(summary['dados']['ingestao']['cabecalho_detectado'])
                self.assertTrue(summary['dados']['transformacoes'])
                latest = self.client.get('/api/analysis/latest', headers={'Origin': origin})
                self.assertEqual(latest.headers['access-control-allow-origin'], origin)
                self.assertEqual(latest.json(), summary)
                preflight = self.client.options('/api/analysis', headers={'Origin': origin, 'Access-Control-Request-Method': 'POST'})
                self.assertEqual(preflight.status_code, 200)

    def test_origem_desconhecida_nao_e_permitida(self):
        response = self.client.options('/api/analysis', headers={'Origin': 'https://exemplo.invalid', 'Access-Control-Request-Method': 'POST'})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('access-control-allow-origin', response.headers)

    def test_post_multitabela_real_json_estrito(self):
        source = Path(__file__).resolve().parents[1] / 'data/samples'
        files = [('files', (path.name, path.read_bytes())) for path in sorted(source.glob('*.csv'))]
        response = self.client.post('/api/analysis', headers={'Origin': 'http://localhost:5174'}, files=files)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['files_processed'], 14)
        self.assertEqual(response.json()['summary']['dados']['quantidade_arquivos'], 14)
        self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5174')
        json.dumps(response.json(), allow_nan=False)

    def test_numpy_pandas_no_bloco_dados(self):
        def pipeline(*args, **kwargs):
            result = executar_dataagent(*args, **kwargs)
            result['dados']['total_valores_nulos'] = np.int64(0)
            result['dados']['score_qualidade'] = np.float64(95.5)
            result['dados']['ingestao']['cabecalho_detectado'] = np.bool_(True)
            result['dados']['transformacoes'] = [
                {'coluna': 'Data', 'antes': pd.Timestamp('2025-01-01'), 'depois': datetime(2025, 1, 2), 'descricao': 'Teste de tipos.'}
            ]
            return result
        with patch('api.analysis.executar_dataagent', side_effect=pipeline):
            response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()['summary']['dados']
        self.assertEqual(data['total_valores_nulos'], 0)
        self.assertEqual(data['score_qualidade'], 95.5)
        self.assertIs(data['ingestao']['cabecalho_detectado'], True)
        self.assertIsInstance(data['transformacoes'][0]['antes'], str)
        json.dumps(response.json(), allow_nan=False)

    def test_nao_finitos_falham_explicitamente_sem_falso_sucesso(self):
        previous = self.post().json()['summary']
        for number in (float('nan'), float('inf'), -float('inf')):
            def pipeline(*args, **kwargs):
                result = executar_dataagent(*args, **kwargs)
                result['dados']['score_qualidade'] = number
                return result
            with patch('api.analysis.executar_dataagent', side_effect=pipeline):
                response = self.post()
            self.assertEqual(response.status_code, 422)
            self.assertIn('detail', response.json())
            self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5174')
            json.dumps(response.json(), allow_nan=False)
            self.assertEqual(self.client.get('/api/analysis/latest').json(), previous)


if __name__ == '__main__':
    unittest.main()
