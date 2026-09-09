"""Apresentação da qualidade pré-ETL e do log real de processamento."""


def gerar_qualidade_dados(diagnostico, problemas, transformacoes, arquivos):
    linhas = diagnostico['quantidade_linhas']
    colunas = diagnostico['quantidade_colunas']
    nulos = int(sum(diagnostico['valores_nulos'].values()))
    celulas = linhas * colunas
    percentual = nulos / celulas * 100 if celulas else None
    duplicadas = diagnostico['linhas_duplicadas']
    issues = [
        {**item, 'nivel': item.get('severidade', item.get('nivel', 'baixa'))}
        if isinstance(item, dict) else {'mensagem': item, 'nivel': 'baixa'}
        for item in problemas
    ]
    ordem = {'alta': 0, 'media': 1, 'baixa': 2}
    issues.sort(key=lambda item: ordem.get(item['nivel'], 3))
    ingestao = diagnostico.get('ingestao', {})
    estruturas = [ingestao] if 'cabecalho_detectado' in ingestao else list(ingestao.values())
    score = None
    if celulas:
        penalidade = min(30, percentual)
        penalidade += min(20, duplicadas / linhas * 100)
        penalidade += min(30, sum({'alta': 10, 'media': 5}.get(i['nivel'], 0) for i in issues))
        penalidade += 10 if any(i.get('cabecalho_detectado') is False for i in estruturas) else 0
        penalidade += min(10, sum(i.get('colunas_vazias_removidas', 0) for i in estruturas))
        score = round(max(0, min(100, 100 - penalidade)), 2)
    classificacao = None if score is None else (
        'excelente' if score >= 90 else 'boa' if score >= 75 else 'atencao' if score >= 50 else 'critica'
    )
    return {
        'arquivos': arquivos,
        'quantidade_arquivos': len(arquivos),
        'status': 'concluida',
        'escopo': 'Tabela analítica após ingestão estrutural e antes do ETL.',
        'quantidade_linhas': linhas,
        'quantidade_colunas': colunas,
        'linhas_duplicadas': duplicadas,
        'total_valores_nulos': nulos,
        'percentual_nulos_geral': round(percentual, 2) if percentual is not None else None,
        'quantidade_problemas': len(issues),
        'score_qualidade': score,
        'classificacao_qualidade': classificacao,
        'problemas': issues,
        'transformacoes': [
            {'tipo': item['tipo_transformacao'], 'coluna': item['coluna'],
             'antes': item['antes'], 'depois': item['depois'], 'descricao': item['detalhes']}
            for item in transformacoes
        ],
        'ingestao': ingestao,
    }
