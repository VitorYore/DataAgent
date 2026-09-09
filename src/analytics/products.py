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


def analisar_produtos(
    df: pd.DataFrame
) -> dict:

    mapeamento = mapear_colunas(
        df
    )

    coluna_produto_id = (
        encontrar_coluna_por_papel(
            mapeamento,
            "produto_id"
        )
    )

    coluna_produto_nome = (
        encontrar_coluna_por_papel(
            mapeamento,
            "produto"
        )
    )

    coluna_agrupamento, mapa_rotulos = (
        preparar_entidade(
            df,
            coluna_produto_id,
            coluna_produto_nome
        )
    )

    if not coluna_agrupamento:

        return {
            "erro": (
                "Não foi possível identificar "
                "uma coluna de produtos."
            )
        }

    coluna_quantidade = (
        encontrar_coluna_por_papel(
            mapeamento,
            "quantidade"
        )
    )

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
        "coluna_produto": (
            coluna_produto_nome
            or coluna_produto_id
        ),

        "coluna_produto_id": (
            coluna_produto_id
        ),

        "quantidade_produtos": int(
            df[coluna_agrupamento]
            .dropna()
            .nunique()
        )
    }

    # ========================================
    # QUANTIDADE
    # ========================================

    if coluna_quantidade:

        quantidade = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[coluna_quantidade]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "mais_vendidos"
        ] = [
            {
                "produto": (
                    formatar_entidade(
                        produto,
                        mapa_rotulos
                    )
                ),
                "produto_id": produto,
                "quantidade": round(
                    float(valor),
                    2
                )
            }
            for produto, valor
            in quantidade.head(5).items()
        ]

    # ========================================
    # FATURAMENTO
    # ========================================

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
            .sum()
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "top_faturamento"
        ] = [
            {
                "produto": (
                    formatar_entidade(
                        produto,
                        mapa_rotulos
                    )
                ),
                "produto_id": produto,
                "faturamento": round(
                    float(valor),
                    2
                )
            }
            for produto, valor
            in faturamento.head(5).items()
        ]

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
            .sum()
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "top_lucro"
        ] = [
            {
                "produto": (
                    formatar_entidade(
                        produto,
                        mapa_rotulos
                    )
                ),
                "produto_id": produto,
                "lucro": round(
                    float(valor),
                    2
                )
            }
            for produto, valor
            in lucro.head(5).items()
        ]

        negativos = lucro[
            lucro < 0
        ]

        resultado[
            "produtos_com_prejuizo"
        ] = [
            {
                "produto": (
                    formatar_entidade(
                        produto,
                        mapa_rotulos
                    )
                ),
                "produto_id": produto,
                "lucro": round(
                    float(valor),
                    2
                )
            }
            for produto, valor
            in negativos.items()
        ]

    # ========================================
    # POTENCIAL DE CRESCIMENTO
    # ========================================

    if (
        coluna_faturamento
        and coluna_lucro
    ):

        desempenho = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[
                [
                    coluna_faturamento,
                    coluna_lucro
                ]
            ]
            .sum()
        )

        media_faturamento = (
            desempenho[
                coluna_faturamento
            ].mean()
        )

        media_lucro = (
            desempenho[
                coluna_lucro
            ].mean()
        )

        oportunidades = []

        for produto, linha in (
            desempenho.iterrows()
        ):

            faturamento = linha[
                coluna_faturamento
            ]

            lucro = linha[
                coluna_lucro
            ]

            if (
                lucro > media_lucro
                and faturamento < media_faturamento
            ):

                oportunidades.append({
                    "produto": (
                        formatar_entidade(
                            produto,
                            mapa_rotulos
                        )
                    ),
                    "produto_id": produto,
                    "faturamento": round(
                        float(faturamento),
                        2
                    ),
                    "lucro": round(
                        float(lucro),
                        2
                    )
                })

        oportunidades.sort(
            key=lambda item: item[
                "lucro"
            ],
            reverse=True
        )

        resultado[
            "oportunidades_crescimento"
        ] = oportunidades[:5]

    return resultado