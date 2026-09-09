import pandas as pd

from src.analytics.column_mapper import (
    mapear_colunas
)

from src.analytics.business import (
    encontrar_coluna_por_papel
)

from src.analytics.entity_helpers import (
    preparar_entidade,
    formatar_entidade
)


def _ranking_clientes(ordenacao, faturamento, lucro, mapa_rotulos, possui_id):
    def valor(serie, cliente):
        numero = serie.get(cliente)
        return None if numero is None or pd.isna(numero) else round(float(numero), 2)

    return [
        {
            "posicao": posicao,
            "cliente": formatar_entidade(cliente, mapa_rotulos),
            "cliente_id": str(cliente) if possui_id else None,
            "faturamento": valor(faturamento, cliente),
            "lucro": valor(lucro, cliente),
        }
        for posicao, cliente in enumerate(ordenacao.head(10).index, start=1)
    ]


def analisar_clientes(
    df: pd.DataFrame
) -> dict:

    mapeamento = mapear_colunas(
        df
    )

    coluna_cliente_id = (
        encontrar_coluna_por_papel(
            mapeamento,
            "cliente_id"
        )
    )

    coluna_cliente_nome = (
        encontrar_coluna_por_papel(
            mapeamento,
            "cliente"
        )
    )

    coluna_agrupamento, mapa_rotulos = (
        preparar_entidade(
            df,
            coluna_cliente_id,
            coluna_cliente_nome
        )
    )

    if not coluna_agrupamento:

        return {
            "erro": (
                "Não foi possível identificar "
                "uma coluna de clientes."
            )
        }

    coluna_faturamento = (
        encontrar_coluna_por_papel(
            mapeamento,
            "faturamento"
        )
    )

    coluna_lucro = (
        encontrar_coluna_por_papel(
            mapeamento,
            "lucro"
        )
    )

    resultado = {
        "participacao_maior_cliente": None,
        "clientes_resultado_negativo": None,
        "ranking_faturamento": [],
        "ranking_lucro": [],
        "insights_clientes": [],
        "coluna_cliente": (
            coluna_cliente_nome
            or coluna_cliente_id
        ),

        "coluna_cliente_id": (
            coluna_cliente_id
        ),

        "quantidade_clientes": int(
            df[coluna_agrupamento]
            .dropna()
            .nunique()
        )
    }

    # ========================================
    # FATURAMENTO
    # ========================================

    faturamento = pd.Series(dtype=float)
    lucro = pd.Series(dtype=float)

    if coluna_faturamento:

        faturamento = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[coluna_faturamento]
            .sum(min_count=1)
            .dropna()
            .sort_values(
                ascending=False
            )
        )

        if not faturamento.empty:

            cliente_id = (
                faturamento.index[0]
            )

            resultado[
                "maior_faturamento"
            ] = {
                "cliente": (
                    formatar_entidade(
                        cliente_id,
                        mapa_rotulos
                    )
                ),
                "cliente_id": cliente_id,
                "faturamento": round(
                    float(
                        faturamento.iloc[0]
                    ),
                    2
                )
            }

            resultado[
                "top_5_faturamento"
            ] = [
                {
                    "cliente": (
                        formatar_entidade(
                            cliente,
                            mapa_rotulos
                        )
                    ),
                    "cliente_id": cliente,
                    "faturamento": round(
                        float(valor),
                        2
                    )
                }
                for cliente, valor
                in faturamento.head(5).items()
            ]

            # O denominador inclui também vendas sem cliente identificável.
            total = df[coluna_faturamento].sum(min_count=1)

            if total != 0:

                resultado["participacao_maior_cliente"] = round(
                    float(faturamento.iloc[0] / total * 100), 2
                )

                resultado[
                    "concentracao_top_5"
                ] = round(
                    float(
                        faturamento.head(5).sum()
                        / total
                        * 100
                    ),
                    2
                )

    # ========================================
    # LUCRO
    # ========================================

    if coluna_lucro:

        lucro = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[coluna_lucro]
            .sum(min_count=1)
            .dropna()
            .sort_values(
                ascending=False
            )
        )

        if not lucro.empty:

            cliente_id = (
                lucro.index[0]
            )

            resultado[
                "maior_lucro"
            ] = {
                "cliente": (
                    formatar_entidade(
                        cliente_id,
                        mapa_rotulos
                    )
                ),
                "cliente_id": cliente_id,
                "lucro": round(
                    float(
                        lucro.iloc[0]
                    ),
                    2
                )
            }

            negativos = lucro[
                lucro < 0
            ]
            resultado["clientes_resultado_negativo"] = int(len(negativos))

            resultado[
                "clientes_com_prejuizo"
            ] = [
                {
                    "cliente": (
                        formatar_entidade(
                            cliente,
                            mapa_rotulos
                        )
                    ),
                    "cliente_id": cliente,
                    "lucro": round(
                        float(valor),
                        2
                    )
                }
                for cliente, valor
                in negativos.items()
            ]

    resultado["ranking_faturamento"] = _ranking_clientes(
        faturamento, faturamento, lucro, mapa_rotulos, bool(coluna_cliente_id)
    )
    resultado["ranking_lucro"] = _ranking_clientes(
        lucro, faturamento, lucro, mapa_rotulos, bool(coluna_cliente_id)
    )

    insights = resultado["insights_clientes"]
    concentracao = resultado.get("concentracao_top_5")
    if concentracao is not None:
        percentual = f"{concentracao:.2f}".replace(".", ",")
        insights.append(f"Os cinco maiores clientes representam {percentual}% do faturamento.")
    participacao = resultado["participacao_maior_cliente"]
    if participacao is not None:
        percentual = f"{participacao:.2f}".replace(".", ",")
        insights.append(f"O maior cliente representa {percentual}% do faturamento total.")
    negativos = resultado["clientes_resultado_negativo"]
    if negativos:
        insights.append(
            "Existe 1 cliente com resultado agregado negativo."
            if negativos == 1
            else f"Existem {negativos} clientes com resultado agregado negativo."
        )
    if not faturamento.empty and not lucro.empty and faturamento.index[0] != lucro.index[0]:
        insights.append(
            "O cliente líder em faturamento é diferente do cliente com maior lucro, "
            "indicando diferenças de rentabilidade na carteira."
        )
    return resultado
