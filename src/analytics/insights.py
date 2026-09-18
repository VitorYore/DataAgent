from src.analytics.insight_engine import criar_insight


def adicionar_insight(
    insights: list,
    tipo: str,
    mensagem: str,
    categoria: str = "geral",
    prioridade: str = "media",
    **contexto
):

    contexto.setdefault("origem", "insights")
    insights.append({
        **criar_insight(categoria, tipo, prioridade, mensagem, **contexto),
        "tipo": tipo,
        "categoria": categoria,
        "prioridade": prioridade,
        "mensagem": mensagem,
        **contexto
    })


def gerar_insights(
    kpis: dict,
    analise_mensal: dict,
    analise_clientes: dict,
    desempenho: dict,
    crescimento: dict = None,
    dimensoes: dict = None,
    produtos: dict = None,
    oportunidades: list = None
) -> list:

    insights = []

    crescimento = crescimento or {}
    dimensoes = dimensoes or {}
    produtos = produtos or {}
    kpis = kpis or {}
    analise_clientes = analise_clientes or {}

    # ========================================
    # CRESCIMENTO
    # ========================================

    if (
        analise_mensal
        and "erro" not in analise_mensal
    ):

        melhor_mes = analise_mensal.get(
            "melhor_mes"
        )

        if melhor_mes:
            nome_metrica = analise_mensal.get("nome_metrica", "Faturamento")
            valor_metrica = melhor_mes.get("valor", melhor_mes.get("faturamento"))
            if valor_metrica is not None:
                adicionar_insight(
                    insights,
                    "positivo",
                    f"O período {melhor_mes['periodo']} apresentou o maior valor de {nome_metrica}, totalizando {valor_metrica}.",
                    "melhor_periodo",
                    "media",
                    valor=valor_metrica,
                    periodo=melhor_mes.get("periodo"),
                    metrica=analise_mensal.get("metrica", "faturamento"),
                )

        variacoes = analise_mensal.get(
            "variacao_mensal",
            {}
        )

        variacoes = {periodo: valor for periodo, valor in (variacoes or {}).items() if valor is not None}
        if variacoes:

            maior_crescimento = max(
                variacoes,
                key=variacoes.get
            )

            maior_queda = min(
                variacoes,
                key=variacoes.get
            )

            if variacoes[
                maior_queda
            ] < 0:

                adicionar_insight(
                    insights,
                    "atencao",
                    (
                        "A maior queda mensal ocorreu "
                        f"em {maior_queda}, com redução "
                        f"de "
                        f"{abs(variacoes[maior_queda])}%."
                    ),
                    'maior_queda',
                    "alta",
                    valor=variacoes[maior_queda], periodo=maior_queda,
                )

            if variacoes[
                maior_crescimento
            ] > 0:

                adicionar_insight(
                    insights,
                    "positivo",
                    (
                        "O maior crescimento mensal "
                        f"ocorreu em {maior_crescimento}, "
                        f"com aumento de "
                        f"{variacoes[maior_crescimento]}%."
                    ),
                    'maior_crescimento',
                    "media",
                    valor=variacoes[maior_crescimento], periodo=maior_crescimento,
                )

    # ========================================
    # TENDÊNCIA
    # ========================================

    if (
        crescimento
        and "erro" not in crescimento
        and "faturamento" in crescimento
    ):

        dados = crescimento[
            "faturamento"
        ]

        if dados.get(
            "tendencia"
        ) == "queda":

            adicionar_insight(
                insights,
                "atencao",
                (
                    "Considerando o período analisado, "
                    "o faturamento apresenta tendência "
                    "de queda "
                    + (f"{abs(dados['evolucao_total'])}%." if dados.get('evolucao_total') is not None else "no período analisado.")
                ),
                'tendencia_faturamento',
                "alta",
                valor=dados.get('evolucao_total'),
            )

    # ========================================
    # RENTABILIDADE
    # ========================================

    if (
        desempenho
        and "erro" not in desempenho
    ):

        quantidade = desempenho.get(
            "quantidade_registros_prejuizo",
            0
        )

        if quantidade > 0:

            adicionar_insight(
                insights,
                "atencao",
                (
                    f"Foram identificados "
                    f"{quantidade} registros com "
                    "resultado negativo"
                    + (f", totalizando {desempenho['prejuizo_total']}." if desempenho.get('prejuizo_total') is not None else ".")
                ),
                'resultado_negativo',
                "alta",
                valor=quantidade,
            )

    # ========================================
    # PRODUTOS
    # ========================================

    mais_vendidos = produtos.get(
        "mais_vendidos",
        []
    )

    top_faturamento = produtos.get(
        "top_faturamento",
        []
    )

    if mais_vendidos:

        item = mais_vendidos[0]

        adicionar_insight(
            insights,
            "informativo",
            (
                f"O produto '{item['produto']}' "
                "apresentou o maior volume de vendas, "
                f"com {item['quantidade']} unidades."
            ),
            'produto_volume',
            "media",
            valor=item.get('quantidade'),
        )

    if top_faturamento:

        item = top_faturamento[0]

        adicionar_insight(
            insights,
            "positivo",
            (
                f"O produto '{item['produto']}' "
                "apresentou o maior faturamento, "
                f"totalizando "
                f"{item['faturamento']}."
            ),
            'produto_faturamento',
            "media",
            valor=item.get('faturamento'),
        )

    if (
        mais_vendidos
        and top_faturamento
        and mais_vendidos[0][
            "produto_id"
        ]
        != top_faturamento[0][
            "produto_id"
        ]
    ):

        adicionar_insight(
            insights,
            "informativo",
            (
                "O produto com maior volume "
                f"('{mais_vendidos[0]['produto']}') "
                "é diferente do produto com maior "
                f"faturamento "
                f"('{top_faturamento[0]['produto']}')."
            ),
            'produto_rentabilidade',
            "media",
            origem='produtos',
        )

    # ========================================
    # ESTOQUE
    # ========================================

    risco = produtos.get(
        "produtos_risco_ruptura",
        []
    )

    if risco:

        item = sorted(
            risco,
            key=lambda produto: produto.get(
                "quantidade",
                0
            ),
            reverse=True
        )[0]

        adicionar_insight(
            insights,
            "atencao",
            (
                f"O produto '{item['produto']}' "
                "está entre os produtos com risco "
                "de ruptura e possui volume relevante "
                "de vendas."
            ),
            'estoque_ruptura',
            "alta",
            origem='produtos',
        )

    excesso = produtos.get(
        "produtos_estoque_excessivo",
        []
    )

    if excesso:

        adicionar_insight(
            insights,
            "informativo",
            (
                f"Foram identificados "
                f"{len(excesso)} produtos com estoque "
                "acima do nível máximo definido."
            ),
            'estoque_excessivo',
            "media",
            valor=len(excesso),
        )

    # ========================================
    # DEVOLUÇÕES
    # ========================================

    devolucoes = produtos.get(
        "maiores_taxas_devolucao",
        []
    )

    devolucoes = [item for item in devolucoes if item.get("taxa_devolucao") is not None]
    if devolucoes:

        item = devolucoes[0]

        adicionar_insight(
            insights,
            "atencao",
            (
                f"O produto '{item['produto']}' "
                "apresentou uma das maiores taxas "
                f"de devolução, com "
                f"{item['taxa_devolucao']}%."
            ),
            'produto_devolucao',
            "media",
            valor=item.get('taxa_devolucao'),
        )

    # ========================================
    # AVALIAÇÕES
    # ========================================

    melhores = produtos.get(
        "melhores_avaliados",
        []
    )

    piores = produtos.get(
        "piores_avaliados",
        []
    )

    if melhores:

        item = melhores[0]

        adicionar_insight(
            insights,
            "positivo",
            (
                f"O produto '{item['produto']}' "
                "está entre os melhores avaliados, "
                f"com nota média de "
                f"{item['avaliacao_media']}."
            ),
            'produto_avaliacao_positiva',
            "media",
            valor=item.get('avaliacao_media'),
        )

    if piores:

        item = piores[0]

        adicionar_insight(
            insights,
            "informativo",
            (
                f"O produto '{item['produto']}' "
                "está entre os produtos com menor "
                f"avaliação média, com nota "
                f"{item['avaliacao_media']}."
            ),
            'produto_avaliacao_negativa',
            "media",
            valor=item.get('avaliacao_media'),
        )

    # ========================================
    # POTENCIAL
    # ========================================

    oportunidades_produtos = (
        produtos.get(
            "oportunidades_crescimento",
            []
        )
    )

    if oportunidades_produtos:

        item = oportunidades_produtos[0]

        adicionar_insight(
            insights,
            "oportunidade",
            (
                f"O produto '{item['produto']}' "
                "apresenta lucro acima da média "
                "e faturamento abaixo da média, "
                "sendo um possível candidato para "
                "investigação de crescimento."
            ),
            'produto_crescimento',
            "media",
            valor=item.get('lucro'),
        )

    # ========================================
    # CLIENTES
    # ========================================

    concentracao = analise_clientes.get(
        "concentracao_top_5"
    )

    if concentracao is not None:

        adicionar_insight(
            insights,
            "informativo",
            (
                "Os 5 maiores clientes representam "
                f"{concentracao}% do faturamento total."
            ),
            'cliente_concentracao',
            "baixa",
            valor=concentracao,
        )

    lider = analise_clientes.get("maior_faturamento") or {}
    if lider.get("cliente") and lider.get("faturamento") is not None:
        adicionar_insight(
            insights, "positivo",
            f"O cliente '{lider['cliente']}' apresentou o maior faturamento da carteira, totalizando {lider['faturamento']}.",
            "cliente_destaque", "media", valor=lider["faturamento"], origem="clientes",
        )

    # Usa rankings já agregados, sem inferir crescimento de uma diferença pequena.
    for chave, categoria, rotulo in (
        ("canal_venda", "canal_desempenho", "canal"),
        ("loja", "loja_desempenho", "loja"),
        ("colaborador", "colaborador_desempenho", "colaborador"),
    ):
        ranking = (dimensoes.get(chave) or {}).get("top_faturamento") or []
        if len(ranking) < 2:
            continue
        primeiro, segundo = ranking[:2]
        valor = primeiro.get("faturamento")
        if valor is None or segundo.get("faturamento") is None or valor <= segundo["faturamento"]:
            continue
        adicionar_insight(
            insights, "positivo",
            f"O destaque de faturamento na dimensão {rotulo} foi '{primeiro['valor']}', totalizando {valor}.",
            categoria, "baixa", valor=valor, origem="dimensoes", metrica="faturamento",
        )

    # ========================================
    # ORDENAR E LIMITAR
    # ========================================

    ordem = {
        "alta": 1,
        "media": 2,
        "baixa": 3
    }

    insights.sort(
        key=lambda item: ordem.get(
            item["prioridade"],
            99
        )
    )

    # O motor do resumo aplica o limite após combinar todas as fontes.
    return insights
