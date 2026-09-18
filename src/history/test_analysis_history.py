import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.app import create_app
from src.history.analysis_history import salvar_analise_historico, listar_historico, obter_analise, obter_ultima_analise, comparar_analises

CSV = b'Cliente,Data,Faturamento,Lucro\nA,2025-01-15,100,40\nB,2025-02-15,200,50\n'


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, summary=None):
        return salvar_analise_historico(summary or {'kpis': {'faturamento_total': 100}, 'status_geral': {'score': 85, 'status': 'saudavel'}, 'dados': {'ignorar': True}}, ['vendas.csv'], self.root)

    def test_salvar_snapshot_compacto(self):
        item = self.save()
        self.assertEqual(set(item), {'id', 'data_analise', 'arquivos', 'kpis', 'score', 'status'})
        self.assertEqual(obter_analise(item['id'], self.root), item)
        self.assertEqual(json.loads((self.root / f"{item['id']}.json").read_text(encoding='utf-8')), item)
        self.assertEqual(list(self.root.glob('*.tmp')), [])

    def test_novo_snapshot_grava_unicode_sem_entidades_html(self):
        summary = {'status_geral': {'status': 'N\u00e3o dispon\u00edvel'}}
        item = self.save(summary)
        content = (self.root / f"{item['id']}.json").read_bytes()
        self.assertIn('N\u00e3o dispon\u00edvel'.encode('utf-8'), content)
        self.assertNotIn(b'&atilde;', content)
        self.assertNotIn(b'&iacute;', content)
        self.assertEqual(obter_analise(item['id'], self.root)['status'], 'N\u00e3o dispon\u00edvel')

    def test_ordem_e_ids_unicos(self):
        first, second = self.save(), self.save()
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual([item['id'] for item in listar_historico(self.root)], [second['id'], first['id']])
        self.assertEqual(obter_ultima_analise(self.root), second)

    def test_vazio_e_uma_analise(self):
        self.assertEqual(listar_historico(self.root), [])
        self.assertIsNone(obter_ultima_analise(self.root))
        self.assertEqual(comparar_analises(None, None)['status'], 'insuficiente')
        self.assertEqual(comparar_analises(self.save(), None)['status'], 'insuficiente')

    def test_comparacao_percentual_e_margem(self):
        result = comparar_analises({'id': 'a', 'kpis': {'faturamento_total': 150, 'margem_lucro': 93.98}}, {'id': 'b', 'kpis': {'faturamento_total': 100, 'margem_lucro': 95.18}})
        self.assertEqual(result['metricas']['faturamento_total']['variacao_percentual'], 50)
        self.assertEqual(result['metricas']['margem_lucro']['variacao_pontos_percentuais'], -1.2)
        self.assertNotIn('variacao_percentual', result['metricas']['margem_lucro'])

    def test_zero_e_metricas_ausentes(self):
        result = comparar_analises({'kpis': {'faturamento_total': 10, 'lucro_total': 5, 'margem_lucro': 2}}, {'kpis': {'faturamento_total': 0, 'margem_lucro': 0}})['metricas']
        self.assertIsNone(result['faturamento_total']['variacao_percentual'])
        self.assertIsNone(result['lucro_total']['anterior'])
        self.assertIsNone(result['lucro_total']['variacao_percentual'])
        self.assertNotIn('ticket_medio', result)
        self.assertEqual(result['margem_lucro']['variacao_pontos_percentuais'], 2)

    def test_campos_ausentes_no_snapshot(self):
        item = salvar_analise_historico({}, pasta=self.root)
        self.assertEqual(item['kpis'], {})
        self.assertIsNone(item['score'])
        self.assertEqual(item['arquivos'], [])

    def test_caminho_invalido(self):
        for identifier in ('../segredo', '..\\segredo', '/absoluto', 'analysis_inexistente'):
            with self.assertRaises(FileNotFoundError):
                obter_analise(identifier, self.root)

    def test_falha_escrita_nao_publica_entrada(self):
        with patch('pathlib.Path.replace', side_effect=OSError('Disco indisponível')):
            with self.assertRaises(OSError):
                self.save()
        self.assertEqual(listar_historico(self.root), [])
        self.assertEqual(list(self.root.glob('*.tmp')), [])

    def test_api_duas_execucoes_e_reinicio(self):
        report = self.root / 'reports/resumo_executivo.json'
        uploads = self.root / 'uploads'
        with contextlib.redirect_stdout(io.StringIO()), TestClient(create_app(report, uploads)) as client:
            self.assertEqual(client.get('/api/analysis/history').json(), [])
            self.assertEqual(client.get('/api/analysis/compare').json()['status'], 'insuficiente')
            first = client.post('/api/analysis', files=[('files', ('vendas.csv', CSV))])
            self.assertEqual(first.status_code, 200)
            self.assertEqual(client.get('/api/analysis/compare').json()['status'], 'insuficiente')
            second = client.post('/api/analysis', files=[('files', ('vendas.csv', CSV.replace(b',100,40', b',200,80')))])
            self.assertEqual(second.status_code, 200)
            history = client.get('/api/analysis/history').json()
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]['id'], second.json()['summary']['analysis_id'])
            full_report = client.get('/api/analysis/' + history[0]['id'])
            self.assertEqual(full_report.status_code, 200)
            self.assertEqual(full_report.json(), second.json()['summary'])
            selected_compare = client.get(f"/api/analysis/compare?left={history[1]['id']}&right={history[0]['id']}")
            self.assertEqual(selected_compare.status_code, 200)
            self.assertEqual(selected_compare.json()['metrics']['faturamento_total']['right'], second.json()['summary']['kpis']['faturamento_total'])
            summary_kpis = second.json()['summary']['kpis']
            self.assertTrue(set(history[0]['kpis']).issubset(summary_kpis))
            self.assertEqual(history[0]['kpis'], {key: summary_kpis[key] for key in history[0]['kpis']})
            self.assertIn('valor_total', history[0]['kpis'])
            self.assertIn('margem_bruta_percentual', history[0]['kpis'])
            self.assertEqual(client.get('/api/analysis/history/' + history[0]['id']).json(), history[0])
            compare = client.get('/api/analysis/compare').json()
            self.assertEqual(compare['metricas']['faturamento_total']['variacao_percentual'], 33.33)
            self.assertEqual(client.get('/api/analysis/history/desconhecido').status_code, 404)
            self.assertEqual(client.get('/api/analysis/latest').json(), second.json()['summary'])
        with TestClient(create_app(report, uploads)) as restarted:
            self.assertEqual(restarted.get('/api/analysis/history').json(), history)
            self.assertEqual(restarted.get('/api/analysis/compare').json(), compare)

    def test_api_analise_falha_nao_entra_no_historico(self):
        with contextlib.redirect_stdout(io.StringIO()), TestClient(create_app(self.root / 'reports/resumo_executivo.json', self.root / 'uploads')) as client:
            for name, content in [('quebrado.xlsx', b'invalido'), ('vendas.csv', b'')]:
                response = client.post('/api/analysis', files=[('files', (name, content))])
                self.assertNotEqual(response.status_code, 200)
                self.assertEqual(client.get('/api/analysis/history').json(), [])

    def test_corrupcao_e_visivel(self):
        item = self.save()
        (self.root / f"{item['id']}.json").write_text('{invalido', encoding='utf-8')
        with self.assertRaises(ValueError):
            listar_historico(self.root)


if __name__ == '__main__':
    unittest.main()
