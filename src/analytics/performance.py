import pandas as pd

from src.analytics.column_mapper import mapear_colunas
from src.analytics.business import encontrar_coluna_por_papel


def analisar_desempenho(
    df: pd.DataFrame,
    dados_temporais: pd.DataFrame | None = None,
) -> dict:

    mapeamento = mapear_colunas(df)

    coluna_data = encontrar_coluna_por_papel(
        mapeamento,
        "data"
    )

    coluna_lucro = encontrar_coluna_por_papel(
        mapeamento,
        "lucro"
    )

    if not coluna_lucro:
        return {
            "erro": (
                "Não foi possível identificar "
                "uma coluna de lucro."
            )
        }

    resultado = {}

    # ========================================
    # 1. RESULTADO GERAL
    # ========================================

    lucro_total = df[coluna_lucro].sum()

    resultado["lucro_total"] = round(
        lucro_total,
        2
    )

    # ========================================
    # 2. REGISTROS COM PREJUÍZO
    # ========================================

    registros_prejuizo = df[
        df[coluna_lucro] < 0
    ]

    resultado[
        "quantidade_registros_prejuizo"
    ] = int(
        len(registros_prejuizo)
    )

    resultado[
        "prejuizo_total"
    ] = round(
        registros_prejuizo[
            coluna_lucro
        ].sum(),
        2
    )

    # ========================================
    # 3. ANÁLISE TEMPORAL DE LUCRO
    # ========================================

    if coluna_data:

        fonte_temporal = dados_temporais if dados_temporais is not None else df
        dados = fonte_temporal.dropna(
            subset=[
                coluna_data,
                coluna_lucro
            ]
        ).copy()

        dados["Periodo"] = (
            dados[coluna_data]
            .dt.to_period("M")
        )

        lucro_mensal = (
            dados
            .groupby("Periodo")[
                coluna_lucro
            ]
            .sum()
            .sort_index()
        )

        if not lucro_mensal.empty:

            melhor_periodo = (
                lucro_mensal.idxmax()
            )

            pior_periodo = (
                lucro_mensal.idxmin()
            )

            resultado[
                "melhor_periodo_lucro"
            ] = {
                "periodo": str(
                    melhor_periodo
                ),
                "lucro": round(
                    lucro_mensal.loc[
                        melhor_periodo
                    ],
                    2
                )
            }

            resultado[
                "pior_periodo_lucro"
            ] = {
                "periodo": str(
                    pior_periodo
                ),
                "lucro": round(
                    lucro_mensal.loc[
                        pior_periodo
                    ],
                    2
                )
            }

            resultado[
                "lucro_mensal"
            ] = {
                str(periodo): round(
                    valor,
                    2
                )
                for periodo, valor
                in lucro_mensal.items()
            }

            periodos_prejuizo = (
                lucro_mensal[
                    lucro_mensal < 0
                ]
            )

            resultado[
                "periodos_com_prejuizo"
            ] = [
                {
                    "periodo": str(
                        periodo
                    ),
                    "lucro": round(
                        valor,
                        2
                    )
                }
                for periodo, valor
                in periodos_prejuizo.items()
            ]

    return resultado