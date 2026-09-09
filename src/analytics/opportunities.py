from src.analytics.insight_engine import criar_insight


def adicionar_oportunidade(
    oportunidades: list,
    tipo: str,
    prioridade: str,
    categoria: str,
    mensagem: str,
    **contexto
):

    contexto.setdefault("origem", "oportunidades")
    oportunidades.append({
        **criar_insight(categoria, tipo, prioridade, mensagem, **contexto),
        "tipo": tipo,
        "prioridade": prioridade,
        "categoria": categoria,
        "mensagem": mensagem,
        **contexto
    })


def analisar_oportunidades(
    crescimento: dict,
    dimensoes: dict,
    analise_clientes: dict,
    desempenho: dict,
    produtos: dict
) -> list:

    oportunidades = []

    crescimento = crescimento or {}
    dimensoes = dimensoes or {}
    analise_clientes = (
        analise_clientes or {}
    )
    desempenho = desempenho or {}
    produtos = produtos or {}

    # ========================================
    # CRESCIMENTO
    # ========================================

    if (
        "erro" not in crescimento
        and "faturamento" in crescimento
    ):

        dados = crescimento[
            "faturamento"
        ]

        tendencia = dados.get(
            "tendencia"
        )

        evolucao = dados.get(
            "evolucao_total"
        )

        if tendencia == "queda":

            adicionar_oportunidade(
                oportunidades,
                "atencao",
                "alta",
                'tendencia_faturamento',
                (
                    "O faturamento apresenta tendência "
                    "de queda"
                    + (f" ({evolucao}%). " if evolucao is not None else ". ")
                    +
                    "Vale investigar os períodos e "
                    "dimensões que mais contribuíram "
                    "para essa redução."
                ),
                valor=evolucao,
            )

        sequencias = dados.get(
            "sequencias_queda",
            []
        )

        if sequencias:

            maior = max(
                sequencias,
                key=len
            )

            periodos = [
                item["periodo"]
                for item in maior
            ]

            adicionar_oportunidade(
                oportunidades,
                "atencao",
                "alta",
                'sequencia_quedas_faturamento',
                (
                    "Foi identificada uma sequência "
                    "de quedas no faturamento nos "
                    "períodos: "
                    + " -> ".join(periodos)
                    + "."
                ),
                periodo=', '.join(periodos),
            )

    # ========================================
    # LUCRO
    # ========================================

    if (
        "erro" not in crescimento
        and "lucro" in crescimento
    ):

        dados = crescimento[
            "lucro"
        ]

        if dados.get(
            "tendencia"
        ) == "queda":

            adicionar_oportunidade(
                oportunidades,
                "atencao",
                "alta",
                'tendencia_lucro',
                (
                    "O lucro apresenta tendência "
                    f"de queda "
                    + (f"({dados['evolucao_total']}%). " if dados.get('evolucao_total') is not None else "no período analisado. ")
                    +
                    "Vale revisar custos, margens "
                    "e fontes de receita."
                ),
                valor=dados.get('evolucao_total'),
            )

    # ========================================
    # RENTABILIDADE
    # ========================================

    quantidade_prejuizo = (
        desempenho.get(
            "quantidade_registros_prejuizo",
            0
        )
    )

    if quantidade_prejuizo > 0:

        adicionar_oportunidade(
            oportunidades,
            "revisao",
            "media",
            'resultado_negativo',
            (
                f"Foram encontrados "
                f"{quantidade_prejuizo} registros "
                "com resultado negativo"
                + (f", totalizando {desempenho['prejuizo_total']}. " if desempenho.get('prejuizo_total') is not None else ". ")
                +
                "Esses registros podem ser investigados "
                "para identificar fontes de perda."
            ),
            valor=quantidade_prejuizo,
        )

    # ========================================
    # PRODUTOS - CRESCIMENTO
    # ========================================

    crescimento_produtos = produtos.get(
        "oportunidades_crescimento",
        []
    )

    for item in (
        crescimento_produtos[:3]
    ):

        adicionar_oportunidade(
            oportunidades,
            "oportunidade",
            "media",
            'produto_crescimento',
            (
                f"O produto '{item['produto']}' "
                "apresenta lucro acima da média "
                "e faturamento abaixo da média, "
                "indicando possível espaço para "
                "crescimento."
            ),
            valor=item.get('lucro'),
        )

    # ========================================
    # ESTOQUE
    # ========================================

    risco_ruptura = produtos.get(
        "produtos_risco_ruptura",
        []
    )

    if risco_ruptura:

        # Priorizar quem vende mais
        ordenados = sorted(
            risco_ruptura,
            key=lambda item: item.get(
                "quantidade",
                0
            ),
            reverse=True
        )

        for item in ordenados[:3]:

            adicionar_oportunidade(
                oportunidades,
                "atencao",
                "alta",
                'estoque_ruptura',
                (
                    f"O produto '{item['produto']}' "
                    "está em risco de ruptura de estoque"
                    + (
                        f", com estoque atual de "
                        f"{item.get('estoque_atual')} "
                        f"e mínimo de "
                        f"{item.get('estoque_minimo')}"
                        if (
                            item.get(
                                "estoque_atual"
                            ) is not None
                            and item.get(
                                "estoque_minimo"
                            ) is not None
                        )
                        else ""
                    )
                    + "."
                ),
                valor=item.get('estoque_atual'),
            )

    excesso = produtos.get(
        "produtos_estoque_excessivo",
        []
    )

    if excesso:

        ordenados = sorted(
            excesso,
            key=lambda item: item.get(
                "quantidade",
                0
            )
        )

        for item in ordenados[:2]:

            adicionar_oportunidade(
                oportunidades,
                "revisao",
                "media",
                'estoque_excessivo',
                (
                    f"O produto '{item['produto']}' "
                    "apresenta estoque elevado em relação "
                    "ao limite definido. Vale avaliar "
                    "giro, compras futuras ou ações "
                    "comerciais."
                ),
                valor=item.get('estoque_atual'),
            )

    # ========================================
    # DEVOLUÇÕES
    # ========================================

    devolucoes = produtos.get(
        "maiores_taxas_devolucao",
        []
    )

    taxa_media = produtos.get(
        "taxa_devolucao_media"
    )

    if devolucoes:

        for item in devolucoes[:3]:

            taxa = item.get(
                "taxa_devolucao"
            )

            if (
                taxa is not None
                and (taxa_media is None or taxa > taxa_media)
            ):

                adicionar_oportunidade(
                    oportunidades,
                    "atencao",
                    "media",
                    'produto_devolucao',
                    (
                        f"O produto '{item['produto']}' "
                        f"possui taxa de devolução de "
                        f"{taxa}%"
                        + (
                            f", acima da média de "
                            f"{taxa_media}%"
                            if taxa_media is not None
                            else ""
                        )
                        + ". Vale investigar motivos "
                        "de devolução e qualidade "
                        "do produto."
                    ),
                    valor=taxa,
                )

    # ========================================
    # AVALIAÇÕES
    # ========================================

    piores = produtos.get(
        "piores_avaliados",
        []
    )

    media_geral = produtos.get(
        "avaliacao_media_geral"
    )

    if piores and media_geral is not None:

        for item in piores[:3]:

            avaliacao = item.get(
                "avaliacao_media"
            )

            if (
                avaliacao is not None
                and avaliacao < media_geral
            ):

                adicionar_oportunidade(
                    oportunidades,
                    "revisao",
                    "media",
                    'produto_avaliacao_negativa',
                    (
                        f"O produto '{item['produto']}' "
                        f"possui avaliação média de "
                        f"{avaliacao}, abaixo da média "
                        f"geral de {media_geral}. "
                        "Vale investigar possíveis "
                        "problemas de qualidade ou "
                        "expectativa do cliente."
                    ),
                    valor=avaliacao,
                )

    # ========================================
    # CLIENTES
    # ========================================

    concentracao = (
        analise_clientes.get(
            "concentracao_top_5"
        )
    )

    if (
        concentracao is not None
        and concentracao < 20
    ):

        adicionar_oportunidade(
            oportunidades,
            "informativo",
            "baixa",
            'cliente_concentracao',
            (
                "Os 5 maiores clientes representam "
                f"{concentracao}% do faturamento. "
                "A receita apresenta baixa "
                "concentração entre os principais "
                "clientes."
            ),
            valor=concentracao,
        )

    # ========================================
    # ORDENAR
    # ========================================

    ordem = {
        "alta": 1,
        "media": 2,
        "baixa": 3
    }

    oportunidades.sort(
        key=lambda item: ordem.get(
            item["prioridade"],
            99
        )
    )

    return oportunidades
