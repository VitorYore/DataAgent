import pandas as pd

from src.analytics.column_mapper import mapear_colunas
from src.analytics.business import encontrar_coluna_por_papel


def analisar_meses(df: pd.DataFrame) -> dict:

    mapeamento = mapear_colunas(df)

    coluna_data = encontrar_coluna_por_papel(
        mapeamento,
        "data"
    )

    coluna_faturamento = encontrar_coluna_por_papel(
        mapeamento,
        "faturamento"
    )

    if not coluna_data or not coluna_faturamento:
        return {
            "erro": (
                "Não foi possível identificar "
                "Data e Faturamento."
            )
        }

    dados = df.dropna(
        subset=[
            coluna_data,
            coluna_faturamento
        ]
    ).copy()

    dados["Periodo"] = (
        dados[coluna_data]
        .dt.to_period("M")
    )

    faturamento_mensal = (
        dados
        .groupby("Periodo")[coluna_faturamento]
        .sum()
        .sort_index()
    )

    quantidade_registros = (
        dados
        .groupby("Periodo")
        .size()
    )

    if faturamento_mensal.empty:
        return {
            "erro": (
                "Não existem dados mensais suficientes."
            )
        }

    # ========================================
    # MELHOR E PIOR MÊS
    # ========================================

    melhor_mes = faturamento_mensal.idxmax()
    pior_mes = faturamento_mensal.idxmin()

    # ========================================
    # VARIAÇÃO ENTRE MESES CONSECUTIVOS
    # ========================================

    variacao_mensal = {}

    periodos = list(
        faturamento_mensal.index
    )

    for indice in range(1, len(periodos)):

        periodo_atual = periodos[indice]
        periodo_anterior = periodos[indice - 1]

        # Verifica se o período anterior é realmente
        # o mês imediatamente anterior
        if (
            periodo_anterior + 1
            != periodo_atual
        ):
            continue

        valor_atual = faturamento_mensal.loc[
            periodo_atual
        ]

        valor_anterior = faturamento_mensal.loc[
            periodo_anterior
        ]

        if valor_anterior == 0:
            continue

        variacao = (
            (valor_atual - valor_anterior)
            / valor_anterior
        ) * 100

        variacao_mensal[
            str(periodo_atual)
        ] = round(
            variacao,
            2
        )

    # ========================================
    # PERÍODOS SUSPEITOS
    # ========================================

    periodos_suspeitos = []

    for periodo, quantidade in quantidade_registros.items():

        if quantidade < 5:

            periodos_suspeitos.append({
                "periodo": str(periodo),
                "registros": int(quantidade),
                "faturamento": round(
                    faturamento_mensal.loc[periodo],
                    2
                )
            })

    return {
        "melhor_mes": {
            "periodo": str(melhor_mes),
            "faturamento": round(
                faturamento_mensal.loc[melhor_mes],
                2
            )
        },

        "pior_mes": {
            "periodo": str(pior_mes),
            "faturamento": round(
                faturamento_mensal.loc[pior_mes],
                2
            )
        },

        "faturamento_mensal": {
            str(periodo): round(valor, 2)
            for periodo, valor
            in faturamento_mensal.items()
        },

        "variacao_mensal": variacao_mensal,

        "periodos_suspeitos": periodos_suspeitos
    }