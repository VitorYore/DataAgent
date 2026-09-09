import unittest

from src.analytics.insight_engine import criar_insight, deduplicar_insights, para_relatorio, selecionar_insights, organizar_listas
from src.analytics.insights import gerar_insights, adicionar_insight
from src.analytics.opportunities import analisar_oportunidades
from src.reports.executive_summary import gerar_resumo_executivo, calcular_status_geral


class InsightEngineTests(unittest.TestCase):
    def test_risco_prevalece_globalmente(self):
        for ordem in (False, True):
            itens = [self.insight(categoria='maior_queda', tipo='informativo', valor=-46.05),
                     self.insight(categoria='maior_queda', tipo='risco', prioridade='baixa')]
            resultado = organizar_listas(itens[::-1] if ordem else itens)
            self.assertEqual(len(resultado['principais_riscos']), 1)
            self.assertEqual(resultado['principais_insights'], [])

    def test_oportunidade_prevalece_globalmente(self):
        resultado = organizar_listas([self.insight(tipo='destaque', prioridade='alta'),
                                     self.insight(tipo='oportunidade')])
        self.assertEqual(len(resultado['oportunidades']), 1)
        self.assertEqual(resultado['principais_insights'], [])

    def test_texto_normalizado_global(self):
        resultado = organizar_listas([
            self.insight(categoria='a', tipo='informativo', texto='  MESMO   TEXTO. '),
            self.insight(categoria='b', tipo='risco', texto='Mesmo texto.'),
            self.insight(categoria='c', tipo='oportunidade', texto='mesmo texto.'),
        ])
        self.assertEqual(len(resultado['principais_riscos']), 1)
        self.assertEqual(resultado['oportunidades'], [])
        self.assertEqual(resultado['principais_insights'], [])

    def test_eventos_distintos_em_listas_distintas(self):
        resultado = organizar_listas([self.insight(), self.insight(categoria='melhor_periodo', tipo='destaque', texto='Melhor período: janeiro.')])
        self.assertEqual(len(resultado['principais_riscos']), 1)
        self.assertEqual(len(resultado['principais_insights']), 1)

    def test_riscos_excedentes_nao_vazam_para_insights(self):
        resultado = organizar_listas([self.insight(categoria=f'risco_{i}', texto=f'Evento {i}') for i in range(10)])
        self.assertEqual(len(resultado['principais_riscos']), 5)
        self.assertEqual(resultado['principais_insights'], [])

    def test_pipeline_vendas_tratadas(self):
        import contextlib
        import io
        import json
        import tempfile
        import pandas as pd
        from pathlib import Path
        from main import executar_pipeline_analitico
        source = Path(__file__).resolve().parents[2] / 'data/processed/vendas_tratadas.csv'
        if not source.exists():
            self.skipTest('Dataset local vendas_tratadas.csv não disponível.')
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            # Este arquivo processado usa ';'; o teste chama o pipeline analítico
            # compartilhado sem alterar a ingestão de uploads nesta correção.
            dados = pd.read_csv(source, sep=';', encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                resumo = executar_pipeline_analitico(dados, origem=source.name, diretorio_saida=root / 'output')
            listas = [resumo[k] for k in ('principais_riscos', 'oportunidades', 'principais_insights')]
            itens = [item for lista in listas for item in lista]
            self.assertEqual(len(itens), len({item['categoria'] for item in itens}))
            self.assertEqual(len(itens), len({' '.join(item['mensagem'].split()).casefold() for item in itens}))
            self.assertTrue(all(i['tipo'] in ('positivo', 'informativo') for i in resumo['principais_insights']))
            analise = json.loads((root / 'output/reports/analise.json').read_text(encoding='utf-8'))
            if not any(i['tipo'] == 'oportunidade' for i in analise['oportunidades'] + analise['insights']):
                self.assertEqual(resumo['oportunidades'], [])

    def insight(self, categoria='tendencia_faturamento', texto='Faturamento apresenta queda.', prioridade='media', tipo='risco', **contexto):
        return criar_insight(categoria, tipo, prioridade, texto, **contexto)

    def test_iguais(self):
        item = self.insight()
        self.assertEqual(deduplicar_insights([item, item]), [item])

    def test_gerador_nao_descarta_prioridade_maior(self):
        itens = []
        adicionar_insight(itens, 'atencao', 'Queda.', 'tendencia_faturamento', 'baixa')
        adicionar_insight(itens, 'atencao', 'Queda.', 'tendencia_faturamento', 'alta')
        self.assertEqual(deduplicar_insights(itens)[0]['prioridade'], 'alta')

    def test_taxa_ausente_nao_gera_alerta(self):
        produtos = {'maiores_taxas_devolucao': [{'produto': 'X', 'taxa_devolucao': None}]}
        self.assertEqual(gerar_insights({}, {}, {}, {}, produtos=produtos), [])
        self.assertEqual(analisar_oportunidades({}, {}, {}, {}, produtos), [])

    def test_especifico_supera_generico(self):
        generico = self.insight(texto='Uma mensagem genérica muito longa sobre faturamento em queda, sem contexto preciso.')
        especifico = self.insight(texto='Faturamento caiu 6,59%.', valor=-6.59)
        self.assertEqual(deduplicar_insights([generico, especifico]), [especifico])

    def test_prioridade_precede_contexto(self):
        alta = self.insight(prioridade='alta')
        baixa = self.insight(prioridade='baixa', valor=-1, periodo='2025-01')
        self.assertEqual(deduplicar_insights([baixa, alta]), [alta])

    def test_categorias_distintas_preservadas(self):
        self.assertEqual(len(deduplicar_insights([self.insight(), self.insight(categoria='tendencia_lucro')])), 2)

    def test_contexto_zero_conta(self):
        especifico = self.insight(valor=0)
        self.assertEqual(deduplicar_insights([self.insight(), especifico]), [especifico])

    def test_tipos_separados(self):
        itens = [self.insight(), self.insight(categoria='produto_crescimento', tipo='oportunidade'),
                 self.insight(categoria='melhor_periodo', tipo='destaque')]
        self.assertEqual([i['categoria'] for i in para_relatorio(itens, tipo='risco')], ['tendencia_faturamento'])
        self.assertEqual([i['categoria'] for i in para_relatorio(itens, tipo='oportunidade')], ['produto_crescimento'])

    def test_mesma_categoria_nao_vira_dois_tipos(self):
        itens = [self.insight(tipo='informativo'), self.insight(tipo='risco', prioridade='alta')]
        self.assertEqual(len(deduplicar_insights(itens)), 1)
        self.assertEqual(para_relatorio(itens, tipo='oportunidade'), [])

    def test_diversidade_e_limite(self):
        itens = [self.insight(categoria=f'produto_{i}', prioridade='alta') for i in range(10)]
        itens += [self.insight(categoria='cliente_destaque', prioridade='baixa')]
        selecionados = selecionar_insights(itens)
        self.assertEqual(len(selecionados), 8)
        self.assertIn('cliente_destaque', [i['categoria'] for i in selecionados])

    def test_poucos_dados_sem_inventar(self):
        self.assertEqual(gerar_insights({}, {}, {}, {}), [])
        self.assertEqual(analisar_oportunidades({}, {}, {}, {}, {}), [])
        resumo = gerar_resumo_executivo({}, {}, {}, {}, {}, {}, [], [])
        for chave in ('principais_riscos', 'oportunidades', 'principais_insights'):
            self.assertEqual(resumo[chave], [])

    def test_metrica_ausente_nao_vira_zero(self):
        crescimento = {'faturamento': {'tendencia': 'queda', 'evolucao_total': None}}
        oportunidades = analisar_oportunidades(crescimento, {}, {}, {}, {})
        insights = gerar_insights({}, {'variacao_mensal': {'2025-01': None}}, {}, {}, crescimento)
        resumo = gerar_resumo_executivo({}, {}, {}, {}, crescimento, {}, oportunidades, insights)
        for item in resumo['principais_insights']:
            self.assertNotIn('None', item['mensagem'])
            self.assertNotIn('0%', item['mensagem'])

    def test_fontes_deduplicadas_e_score_preservado(self):
        crescimento = {'faturamento': {'tendencia': 'queda', 'evolucao_total': -6.59}}
        desempenho = {'quantidade_registros_prejuizo': 3, 'prejuizo_total': -40}
        oportunidades = analisar_oportunidades(crescimento, {}, {}, desempenho, {})
        insights = gerar_insights({}, {}, {}, desempenho, crescimento)
        resumo = gerar_resumo_executivo({}, {}, {}, desempenho, crescimento, {}, oportunidades, insights)
        self.assertEqual(resumo['status_geral'], calcular_status_geral(crescimento, desempenho, oportunidades))
        self.assertEqual(len(resumo['principais_riscos']), 2)
        for chave in ('principais_riscos', 'oportunidades', 'principais_insights'):
            lista = resumo[chave]
            self.assertEqual(len(lista), len({i['categoria'] for i in lista}))
            self.assertEqual(len(lista), len({i['mensagem'] for i in lista}))

    def test_contrato_externo_nao_expoe_modelo(self):
        item = para_relatorio([self.insight(valor=-6.59, origem='temporal')])[0]
        self.assertEqual(set(item), {'tipo', 'categoria', 'prioridade', 'mensagem'})
        self.assertEqual(item['tipo'], 'atencao')

    def test_listas_especificas_preservadas(self):
        clientes = {'insights_clientes': ['Os cinco maiores clientes representam 10% do faturamento.']}
        resumo = gerar_resumo_executivo({}, {}, clientes, {}, {}, {}, [], [])
        self.assertEqual(resumo['clientes']['insights_clientes'], clientes['insights_clientes'])

    def test_dimensoes_sem_inferir_oportunidade(self):
        dimensoes = {'canal_venda': {'top_faturamento': [{'valor': 'Online', 'faturamento': 101}, {'valor': 'Físico', 'faturamento': 100}]}}
        itens = gerar_insights({}, {}, {}, {}, dimensoes=dimensoes)
        self.assertEqual(para_relatorio(itens, tipo='oportunidade'), [])
        self.assertEqual(itens[0]['categoria'], 'canal_desempenho')


if __name__ == '__main__':
    unittest.main()
