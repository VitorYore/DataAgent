"""Apresentação da qualidade pré-ETL e do log real de processamento."""

import pandas as pd


def auditar_coerencia_financeira(dataframe, mapeamento=None, tolerancia_centavos=0.01):
    """Audita Faturamento - Custo = Lucro sem alterar as métricas originais."""
    if dataframe is None or dataframe.empty:
        return None
    if mapeamento is None:
        from src.analytics.column_mapper import mapear_colunas
        mapeamento = mapear_colunas(dataframe)
    from src.analytics.business import encontrar_coluna_por_papel

    columns = {
        concept: encontrar_coluna_por_papel(mapeamento, concept)
        for concept in ("faturamento", "custo", "lucro")
    }
    if not all(columns.values()):
        return None

    numeric = {
        concept: pd.to_numeric(dataframe[column], errors="coerce")
        for concept, column in columns.items()
    }
    audit = {
        concept: {
            "coluna": columns[concept],
            "linhas_validas": int(values.notna().sum()),
            "nulos": int(values.isna().sum()),
            "soma": round(float(values.sum()), 2) if values.notna().any() else None,
        }
        for concept, values in numeric.items()
    }
    complete = pd.concat(numeric, axis=1).dropna()
    if complete.empty:
        audit.update({
            "linhas_com_tres_metricas": 0,
            "tolerancia": tolerancia_centavos,
            "linhas_reconciliadas": 0,
            "percentual_reconciliado": None,
            "somas_linhas_com_tres_metricas": {},
            "residuo_total": None,
            "limite_percentual_reconciliado": 50,
            "erro_absoluto_medio": None,
            "erro_mediano_absoluto": None,
            "residuo_mediano": None,
            "status": "insuficiente",
        })
        return audit

    residual = complete["faturamento"] - complete["custo"] - complete["lucro"]
    absolute_error = residual.abs()
    reconciled = absolute_error.le(tolerancia_centavos)
    percent_reconciled = float(reconciled.mean() * 100)
    audit.update({
        "linhas_com_tres_metricas": int(len(complete)),
        "tolerancia": tolerancia_centavos,
        "linhas_reconciliadas": int(reconciled.sum()),
        "linhas_nao_reconciliadas": int((~reconciled).sum()),
        "somas_linhas_com_tres_metricas": {
            concept: round(float(complete[concept].sum()), 2) for concept in columns
        },
        "residuo_total": round(float(residual.sum()), 2),
        "limite_percentual_reconciliado": 50,
        "percentual_reconciliado": round(percent_reconciled, 2),
        "erro_absoluto_medio": round(float(absolute_error.mean()), 2),
        "erro_mediano_absoluto": round(float(absolute_error.median()), 2),
        "residuo_mediano": round(float(residual.median()), 2),
        "status": "inconsistente" if percent_reconciled < 50 else "coerente",
        "exemplos_residuos": [
            {
                "faturamento": round(float(row.faturamento), 2),
                "custo": round(float(row.custo), 2),
                "lucro": round(float(row.lucro), 2),
                "residuo": round(float(row.residuo), 2),
            }
            for row in complete.assign(residuo=residual).head(5).itertuples()
        ],
    })
    return audit


def gerar_qualidade_dados(diagnostico, problemas, transformacoes, arquivos, dataframe=None, mapeamento=None):
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
    coerencia_metricas = auditar_coerencia_financeira(dataframe, mapeamento)
    if coerencia_metricas and coerencia_metricas.get('status') == 'inconsistente':
        issues.append({
            'nivel': 'media',
            'tipo': 'incoerencia_metricas_financeiras',
            'mensagem': (
                'Faturamento, Custo e Lucro não reconciliam na maior parte dos registros '
                f'({coerencia_metricas["percentual_reconciliado"]}% conciliados; '
                f'tolerância de R$ {coerencia_metricas["tolerancia"]:.2f}). '
                'Os valores originais foram preservados.'
            ),
        })
    anomalias_temporais = diagnostico.get('anomalias_temporais')
    if anomalias_temporais and anomalias_temporais.get('quantidade'):
        issues.append({
            'nivel': 'media',
            'tipo': 'data_temporal_anomala',
            'mensagem': (
                f"{anomalias_temporais['quantidade']} datas estao fora do periodo predominante "
                "e foram desconsideradas somente nas analises temporais."
            ),
        })
    ordem = {'alta': 0, 'media': 1, 'baixa': 2}
    issues.sort(key=lambda item: ordem.get(item['nivel'], 3))
    ingestao = diagnostico.get('ingestao', {})
    estruturas = [ingestao] if 'cabecalho_detectado' in ingestao else list(ingestao.values())
    normalizacoes = []
    vistos = set()
    for estrutura in estruturas:
        candidatos = list(estrutura.get('diagnosticos_abas', {}).values())
        if estrutura.get('normalizacao'):
            candidatos.append(estrutura['normalizacao'])
        for normalizacao in candidatos:
            origem = str(normalizacao.get('origem'))
            if origem in vistos or 'registros_extraidos' not in normalizacao:
                continue
            vistos.add(origem)
            normalizacoes.append(normalizacao)
    for normalizacao in normalizacoes:
        issues.append({'nivel': 'baixa', 'tipo': 'normalizacao_estrutural', 'mensagem': (
            f"Normalização estrutural: {normalizacao['registros_extraidos']} registros identificados; "
            f"{normalizacao['linhas_separadas']} linhas separadas e preservadas na auditoria."
        )})
        if normalizacao.get('formulas_indisponiveis'):
            issues.append({'nivel': 'media', 'tipo': 'formulas_indisponiveis', 'mensagem': f"{len(normalizacao['formulas_indisponiveis'])} fórmulas sem resultado armazenado foram preservadas na auditoria; as respectivas células permanecem indisponíveis, sem recálculo."})
        if normalizacao.get('residuais_preservados'):
            issues.append({'nivel': 'media', 'tipo': 'residuais_preservados', 'mensagem': f"{normalizacao['linhas_desconhecidas']} linhas residuais não transacionais foram preservadas para revisão e não integram os dados analisados."})
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
        ] + [
            {'tipo': 'normalizacao_estrutural', 'descricao': (
                f"{n['linhas_resumo']} linhas de resumo e {n['linhas_periodo']} separadores de período "
                f"preservados fora dos registros; {len(n['transformacoes'])} transformações estruturais auditadas."
            )}
            for n in normalizacoes
        ],
        'ingestao': ingestao,
        'anomalias_temporais': anomalias_temporais,
        'coerencia_metricas': coerencia_metricas,
    }
