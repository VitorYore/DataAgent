from src.analytics.insight_engine import para_relatorio, organizar_listas
from typing import Any


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================


def formatar_valor(
    valor: Any,
    casas: int = 2
):

    if valor is None:
        return None

    if isinstance(
        valor,
        (int, float)
    ):

        return round(
            float(valor),
            casas
        )

    return valor


def pegar_primeiro(
    dados: list | None
):

    if not dados:
        return None

    return dados[0]


# =========================================================
# RESUMO DOS KPIS
# =========================================================


def gerar_resumo_kpis(
    kpis: dict
) -> dict:

    return {

        "faturamento_total": (
            formatar_valor(
                kpis.get(
                    "faturamento_total"
                )
            )
        ),

        "lucro_total": (
            formatar_valor(
                kpis.get(
                    "lucro_total"
                )
            )
        ),

        "custo_total": (
            formatar_valor(
                kpis.get(
                    "custo_total"
                )
            )
        ),

        "margem_lucro": (
            formatar_valor(
                kpis.get(
                    "margem_lucro"
                )
            )
        ),

        "ticket_medio": (
            formatar_valor(
                kpis.get(
                    "ticket_medio"
                )
            )
        ),

        "quantidade_pedidos": (
            kpis.get(
                "quantidade_pedidos"
            )
        ),

        "quantidade_vendida": (
            formatar_valor(
                kpis.get(
                    "quantidade_vendida"
                )
            )
        )
    }


# =========================================================
# SÉRIE TEMPORAL
# =========================================================


def gerar_serie_temporal(
    analise_mensal: dict,
    desempenho: dict
) -> list:

    """
    Constrói uma série temporal consolidada para o frontend.

    Usa:
    - faturamento_mensal
    - lucro_mensal

    Exemplo:

    [
        {
            "periodo": "2022-01",
            "faturamento": 100000,
            "lucro": 80000
        }
    ]
    """

    if (
        not analise_mensal
        or "erro" in analise_mensal
    ):

        return []

    faturamento_mensal = (
        analise_mensal.get(
            "faturamento_mensal",
            {}
        )
    )

    lucro_mensal = {}

    if (
        desempenho
        and "erro" not in desempenho
    ):

        lucro_mensal = (
            desempenho.get(
                "lucro_mensal",
                {}
            )
        )

    periodos = sorted(
        set(
            faturamento_mensal.keys()
        ).union(
            lucro_mensal.keys()
        )
    )

    serie = []

    for periodo in periodos:

        item = {
            "periodo": periodo
        }

        faturamento = (
            faturamento_mensal.get(
                periodo
            )
        )

        lucro = (
            lucro_mensal.get(
                periodo
            )
        )

        if faturamento is not None:

            item[
                "faturamento"
            ] = formatar_valor(
                faturamento
            )

        if lucro is not None:

            item[
                "lucro"
            ] = formatar_valor(
                lucro
            )

        serie.append(
            item
        )

    return serie


# =========================================================
# RESUMO TEMPORAL
# =========================================================


def gerar_resumo_temporal(
    analise_mensal: dict,
    crescimento: dict,
    desempenho: dict
) -> dict:

    resultado = {}

    if (
        analise_mensal
        and "erro"
        not in analise_mensal
    ):

        melhor = (
            analise_mensal.get(
                "melhor_mes"
            )
        )

        pior = (
            analise_mensal.get(
                "pior_mes"
            )
        )

        if melhor:

            resultado[
                "melhor_periodo"
            ] = {
                "periodo": (
                    melhor.get(
                        "periodo"
                    )
                ),

                "faturamento": (
                    formatar_valor(
                        melhor.get(
                            "faturamento"
                        )
                    )
                )
            }

        if pior:

            resultado[
                "pior_periodo"
            ] = {
                "periodo": (
                    pior.get(
                        "periodo"
                    )
                ),

                "faturamento": (
                    formatar_valor(
                        pior.get(
                            "faturamento"
                        )
                    )
                )
            }

    # =========================================
    # TENDÊNCIA
    # =========================================

    if (
        crescimento
        and "erro"
        not in crescimento
        and "faturamento"
        in crescimento
    ):

        dados = crescimento[
            "faturamento"
        ]

        resultado[
            "tendencia_faturamento"
        ] = (
            dados.get(
                "tendencia"
            )
        )

        resultado[
            "evolucao_faturamento"
        ] = (
            formatar_valor(
                dados.get(
                    "evolucao_total"
                )
            )
        )

        maior_crescimento = (
            dados.get(
                "maior_crescimento"
            )
        )

        maior_queda = (
            dados.get(
                "maior_queda"
            )
        )

        if maior_crescimento:

            resultado[
                "maior_crescimento"
            ] = {
                "periodo": (
                    maior_crescimento.get(
                        "periodo"
                    )
                ),

                "variacao": (
                    formatar_valor(
                        maior_crescimento.get(
                            "variacao"
                        )
                    )
                )
            }

        if maior_queda:

            resultado[
                "maior_queda"
            ] = {
                "periodo": (
                    maior_queda.get(
                        "periodo"
                    )
                ),

                "variacao": (
                    formatar_valor(
                        maior_queda.get(
                            "variacao"
                        )
                    )
                )
            }

    # =========================================
    # NOVA SÉRIE PARA O FRONT
    # =========================================

    resultado[
        "serie_temporal"
    ] = gerar_serie_temporal(
        analise_mensal,
        desempenho
    )

    return resultado


# =========================================================
# RESUMO DE CLIENTES
# =========================================================


def gerar_resumo_clientes(
    analise_clientes: dict
) -> dict:

    if (
        not analise_clientes
        or "erro"
        in analise_clientes
    ):

        return {}

    resultado = {
        "participacao_maior_cliente": analise_clientes.get("participacao_maior_cliente"),
        "clientes_resultado_negativo": analise_clientes.get("clientes_resultado_negativo"),
        "ranking_faturamento": analise_clientes.get("ranking_faturamento", []),
        "ranking_lucro": analise_clientes.get("ranking_lucro", []),
        "insights_clientes": analise_clientes.get("insights_clientes", []),
        "quantidade_clientes": (
            analise_clientes.get(
                "quantidade_clientes"
            )
        )
    }

    maior_faturamento = (
        analise_clientes.get(
            "maior_faturamento"
        )
    )

    maior_lucro = (
        analise_clientes.get(
            "maior_lucro"
        )
    )

    if maior_faturamento:

        resultado[
            "cliente_maior_faturamento"
        ] = {
            "cliente": (
                maior_faturamento.get(
                    "cliente"
                )
            ),

            "faturamento": (
                formatar_valor(
                    maior_faturamento.get(
                        "faturamento"
                    )
                )
            )
        }

    if maior_lucro:

        resultado[
            "cliente_maior_lucro"
        ] = {
            "cliente": (
                maior_lucro.get(
                    "cliente"
                )
            ),

            "lucro": (
                formatar_valor(
                    maior_lucro.get(
                        "lucro"
                    )
                )
            )
        }

    resultado[
        "concentracao_top_5"
    ] = (
        formatar_valor(
            analise_clientes.get(
                "concentracao_top_5"
            )
        )
    )

    return resultado


# =========================================================
# RANKING DE PRODUTOS
# =========================================================


def gerar_ranking_produtos(
    produtos: dict,
    limite: int = 10
) -> list:

    """
    Gera um ranking consolidado para o frontend.

    Usa detalhes_produtos quando disponíveis.

    Ordenação principal:
    faturamento decrescente.

    Campos disponíveis:
    - produto
    - produto_id
    - quantidade
    - faturamento
    - lucro
    - avaliacao_media
    - estoque_atual
    - taxa_devolucao
    """

    if (
        not produtos
        or "erro" in produtos
    ):

        return []

    detalhes = produtos.get(
        "detalhes_produtos",
        []
    )

    if not detalhes:

        # Fallback simples usando os rankings
        # já existentes.
        candidatos = {}

        for item in produtos.get(
            "mais_vendidos",
            []
        ):

            produto_id = item.get(
                "produto_id"
            )

            candidatos[
                produto_id
            ] = {
                **candidatos.get(
                    produto_id,
                    {}
                ),
                **item
            }

        for item in produtos.get(
            "top_faturamento",
            []
        ):

            produto_id = item.get(
                "produto_id"
            )

            candidatos[
                produto_id
            ] = {
                **candidatos.get(
                    produto_id,
                    {}
                ),
                **item
            }

        for item in produtos.get(
            "top_lucro",
            []
        ):

            produto_id = item.get(
                "produto_id"
            )

            candidatos[
                produto_id
            ] = {
                **candidatos.get(
                    produto_id,
                    {}
                ),
                **item
            }

        detalhes = list(
            candidatos.values()
        )

    ranking = []

    for item in detalhes:

        ranking.append({
            "produto": (
                item.get(
                    "produto"
                )
            ),

            "produto_id": (
                item.get(
                    "produto_id"
                )
            ),

            "quantidade": (
                formatar_valor(
                    item.get(
                        "quantidade"
                    )
                )
            ),

            "faturamento": (
                formatar_valor(
                    item.get(
                        "faturamento"
                    )
                )
            ),

            "lucro": (
                formatar_valor(
                    item.get(
                        "lucro"
                    )
                )
            ),

            "avaliacao_media": (
                formatar_valor(
                    item.get(
                        "avaliacao_media"
                    )
                )
            ),

            "estoque_atual": (
                formatar_valor(
                    item.get(
                        "estoque_atual"
                    )
                )
            ),

            "taxa_devolucao": (
                formatar_valor(
                    item.get(
                        "taxa_devolucao"
                    )
                )
            )
        })

    ranking.sort(
        key=lambda item: (
            item.get(
                "faturamento"
            )
            or 0
        ),
        reverse=True
    )

    # =========================================
    # POSIÇÃO NO RANKING
    # =========================================

    ranking_final = []

    for posicao, item in enumerate(
        ranking[:limite],
        start=1
    ):

        ranking_final.append({
            "posicao": posicao,
            **item
        })

    return ranking_final


# =========================================================
# RESUMO DE PRODUTOS
# =========================================================


def gerar_resumo_produtos(
    produtos: dict
) -> dict:

    if (
        not produtos
        or "erro"
        in produtos
    ):

        return {}

    resultado = {
        "quantidade_produtos": (
            produtos.get(
                "quantidade_produtos"
            )
        )
    }

    # =========================================
    # MAIS VENDIDO
    # =========================================

    mais_vendido = pegar_primeiro(
        produtos.get(
            "mais_vendidos"
        )
    )

    if mais_vendido:

        resultado[
            "produto_mais_vendido"
        ] = {
            "produto": (
                mais_vendido.get(
                    "produto"
                )
            ),

            "quantidade": (
                formatar_valor(
                    mais_vendido.get(
                        "quantidade"
                    )
                )
            )
        }

    # =========================================
    # MAIOR FATURAMENTO
    # =========================================

    maior_faturamento = pegar_primeiro(
        produtos.get(
            "top_faturamento"
        )
    )

    if maior_faturamento:

        resultado[
            "produto_maior_faturamento"
        ] = {
            "produto": (
                maior_faturamento.get(
                    "produto"
                )
            ),

            "faturamento": (
                formatar_valor(
                    maior_faturamento.get(
                        "faturamento"
                    )
                )
            )
        }

    # =========================================
    # MAIOR LUCRO
    # =========================================

    maior_lucro = pegar_primeiro(
        produtos.get(
            "top_lucro"
        )
    )

    if maior_lucro:

        resultado[
            "produto_maior_lucro"
        ] = {
            "produto": (
                maior_lucro.get(
                    "produto"
                )
            ),

            "lucro": (
                formatar_valor(
                    maior_lucro.get(
                        "lucro"
                    )
                )
            )
        }

    # =========================================
    # ESTOQUE
    # =========================================

    risco_ruptura = produtos.get(
        "produtos_risco_ruptura",
        []
    )

    estoque_excessivo = produtos.get(
        "produtos_estoque_excessivo",
        []
    )

    resultado[
        "produtos_risco_ruptura"
    ] = len(
        risco_ruptura
    )

    resultado[
        "produtos_estoque_excessivo"
    ] = len(
        estoque_excessivo
    )

    # =========================================
    # AVALIAÇÕES
    # =========================================

    resultado[
        "avaliacao_media_geral"
    ] = (
        formatar_valor(
            produtos.get(
                "avaliacao_media_geral"
            )
        )
    )

    # =========================================
    # DEVOLUÇÕES
    # =========================================

    resultado[
        "taxa_devolucao_media"
    ] = (
        formatar_valor(
            produtos.get(
                "taxa_devolucao_media"
            )
        )
    )

    # =========================================
    # NOVO RANKING
    # =========================================

    resultado[
        "ranking_produtos"
    ] = gerar_ranking_produtos(
        produtos,
        limite=10
    )

    return resultado


# =========================================================
# RISCOS
# =========================================================


def gerar_riscos(oportunidades: list, insights: list, limite: int = 5) -> list:
    return para_relatorio((oportunidades or []) + (insights or []), tipo="risco", limite=limite)


def gerar_oportunidades_principais(oportunidades: list, limite: int = 5) -> list:
    return para_relatorio(oportunidades, tipo="oportunidade", limite=limite)


def gerar_principais_insights(insights: list, limite: int = 8) -> list:
    return para_relatorio(insights, limite=limite, diversidade=True)


# =========================================================
# STATUS GERAL
# =========================================================


def calcular_status_geral(
    crescimento: dict,
    desempenho: dict,
    oportunidades: list
) -> dict:

    score = 100

    motivos = []

    if (
        crescimento
        and "faturamento"
        in crescimento
    ):

        faturamento = crescimento[
            "faturamento"
        ]

        if faturamento.get(
            "tendencia"
        ) == "queda":

            score -= 20

            motivos.append(
                "Faturamento apresenta "
                "tendência de queda."
            )

    if (
        crescimento
        and "lucro"
        in crescimento
    ):

        lucro = crescimento[
            "lucro"
        ]

        if lucro.get(
            "tendencia"
        ) == "queda":

            score -= 20

            motivos.append(
                "Lucro apresenta "
                "tendência de queda."
            )

    registros_prejuizo = (
        desempenho.get(
            "quantidade_registros_prejuizo",
            0
        )
        if desempenho
        else 0
    )

    if registros_prejuizo > 0:

        score -= 10

        motivos.append(
            "Existem registros "
            "com resultado negativo."
        )

    alertas_altos = sum(
        1
        for item in oportunidades or []
        if (
            item.get(
                "prioridade"
            )
            == "alta"
            and item.get(
                "tipo"
            )
            in [
                "atencao",
                "revisao"
            ]
        )
    )

    score -= min(
        alertas_altos * 5,
        20
    )

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 80:

        status = "saudavel"

    elif score >= 60:

        status = "atencao"

    else:

        status = "critico"

    return {
        "score": score,
        "status": status,
        "motivos": motivos
    }


# =========================================================
# RESUMO EXECUTIVO COMPLETO
# =========================================================


def gerar_resumo_executivo(
    kpis: dict,
    analise_mensal: dict,
    analise_clientes: dict,
    desempenho: dict,
    crescimento: dict,
    produtos: dict,
    oportunidades: list,
    insights: list
) -> dict:

    resumo = {

        "status_geral": (
            calcular_status_geral(
                crescimento,
                desempenho,
                oportunidades
            )
        ),

        "kpis": (
            gerar_resumo_kpis(
                kpis
            )
        ),

        "temporal": (
            gerar_resumo_temporal(
                analise_mensal,
                crescimento,
                desempenho
            )
        ),

        "clientes": (
            gerar_resumo_clientes(
                analise_clientes
            )
        ),

        "produtos": (
            gerar_resumo_produtos(
                produtos
            )
        ),

        **organizar_listas((oportunidades or []) + (insights or [])),
    }

    return resumo
