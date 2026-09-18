import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app


class TextEncodingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.app = create_app(self.root / 'reports/resumo_executivo.json', self.root / 'data/uploads')
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def test_new_analysis_persists_unicode_in_history_and_http(self):
        filename = 'Análise Período Métricas Qualidade Histórico Comparação Crítica Atenção Evolução Participação Concentração Não disponível.csv'
        data = b'data,faturamento\n2025-01-15,100\n2025-02-15,200\n2025-03-15,300\n'
        with redirect_stdout(io.StringIO()):
            response = self.client.post('/api/analysis', files=[('files', (filename, data, 'text/csv'))])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'success')
        history = self.client.get('/api/analysis/history')
        item = history.json()[0]
        self.assertEqual(item['arquivos'], [filename])
        self.assertIn(filename.encode('utf-8'), history.content)
        folder = self.app.state.analysis_runner.history
        for path in (folder / 'index.json', folder / (item['id'] + '.json')):
            content = path.read_text(encoding='utf-8')
            self.assertIn(filename, content)
            self.assertNotIn('&atilde;', content)
            self.assertNotIn('per?odo', content)
        detail = (folder / 'details' / (item['id'] + '.json')).read_text(encoding='utf-8')
        self.assertIn('O período', detail)
        self.assertNotIn('per?odo', detail)

    def test_legacy_history_is_not_rewritten_by_reading(self):
        folder = self.app.state.analysis_runner.history
        folder.mkdir(parents=True)
        item = {'id': 'analysis-legacy', 'status': 'N&atilde;o dispon&iacute;vel',
                'arquivos': ['per?odo.csv'], 'period': {'start': '1017-02', 'end': '2048-04'}}
        path = folder / 'index.json'
        original = json.dumps({'version': 1, 'items': [item]}, ensure_ascii=False).encode('utf-8')
        path.write_bytes(original)
        self.assertEqual(self.client.get('/api/analysis/history').json(), [item])
        self.assertEqual(path.read_bytes(), original)

    def test_api_errors_have_canonical_unicode(self):
        response = self.client.get('/api/analysis/compare?left=missing&right=missing')
        self.assertEqual(response.json()['detail'], 'Selecione duas análises diferentes.')
        response = self.client.get('/api/analysis/missing')
        self.assertEqual(response.json()['detail'], 'Relatório completo da análise não encontrado.')
        response = self.client.get('/api/analysis/missing/mapping')
        self.assertEqual(response.json()['detail'], 'Análise pendente não encontrada.')
