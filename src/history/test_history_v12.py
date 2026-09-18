import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.history.analysis_history import novo_analysis_id, salvar_analise_historico
from src.history.history_index import listar_indice, obter_resumo, persistir_resumo


class HistoryV12Tests(unittest.TestCase):
    def test_index_keeps_light_metadata_and_detail_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            identifier = novo_analysis_id()
            summary = {'analysis_id': identifier, 'status_geral': {'score': 80, 'status': 'atencao'},
                       'kpis': {'valor_total': 100, 'faturamento_total': None},
                       'dados': {'quantidade_linhas': 4, 'quantidade_colunas': 2,
                                 'mapeamento_semantico': {'origens': {'coluna_2': {'origem': 'cabecalho_posterior'}}}},
                       'temporal': {'serie_temporal': [{'periodo': '2026-01'}]}}
            item = salvar_analise_historico(summary, ['a.csv', 'b.csv'], root)
            persistir_resumo(summary, item, root)
            listing = listar_indice(root)
            self.assertEqual(listing[0]['dataset'], {'rows': 4, 'columns': 2})
            self.assertEqual(listing[0]['period'], {'start': '2026-01', 'end': '2026-01'})
            self.assertEqual(listing[0]['available_metrics'], ['valor_total'])
            self.assertEqual(listing[0]['mode'], 'multi')
            self.assertTrue(listing[0]['report_available'])
            self.assertEqual(obter_resumo(identifier, root), summary)

    def test_api_history_detail_compare_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / 'reports' / 'latest.json'
            app = create_app(report, root / 'uploads')
            folder = app.state.analysis_runner.history
            ids = [novo_analysis_id(), novo_analysis_id()]
            for number, identifier in enumerate(ids, start=1):
                summary = {'analysis_id': identifier, 'status_geral': {'score': 85, 'status': 'saudavel'},
                           'kpis': {'valor_total': number * 100, 'faturamento_total': None},
                           'dados': {'quantidade_linhas': 5, 'quantidade_colunas': 2},
                           'temporal': {'serie_temporal': []}}
                item = salvar_analise_historico(summary, [f'{number}.csv'], folder)
                persistir_resumo(summary, item, folder)
            with TestClient(app) as client:
                history = client.get('/api/analysis/history').json()
                self.assertEqual(len(history), 2)
                self.assertEqual(client.get('/api/analysis/' + ids[0]).json()['kpis']['valor_total'], 100)
                result = client.get(f'/api/analysis/compare?left={ids[0]}&right={ids[1]}').json()
                self.assertEqual(result['metrics']['valor_total']['absolute_change'], 100)
                self.assertEqual(client.get('/api/analysis/../secret').status_code, 404)


if __name__ == '__main__':
    unittest.main()
