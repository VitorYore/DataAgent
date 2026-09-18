import pandas as pd

from src.analytics.column_mapper import mapear_colunas
from src.analytics.business import encontrar_coluna_por_papel


def analisar_meses(df: pd.DataFrame) -> dict:

    mapeamento = mapear_colunas(df)

    coluna_data = encontrar_coluna_por_papel(
        mapeamento,
        "data"
    )

    metricas = (
        ("faturamento", "Faturamento"),
        ("valor_total", "Valor Total"),
        ("valor_com_desconto", "Valor com Desconto"),
        ("margem_bruta", "Margem Bruta"),
        ("lucro", "Lucro"),
        ("custo", "Custo"),
    )
    metrica, nome_metrica, coluna_valor = next(
        ((papel, rotulo, encontrar_coluna_por_papel(mapeamento, papel))
         for papel, rotulo in metricas
         if encontrar_coluna_por_papel(mapeamento, papel)),
        (None, None, None),
    )

    if not coluna_data or not coluna_valor:
        return {
            "erro": (
                "Não foi possível identificar "
                "Data e uma métrica monetária semântica."
            )
        }

    dados = df.dropna(
        subset=[
            coluna_data,
            coluna_valor
        ]
    ).copy()
    if not pd.api.types.is_datetime64_any_dtype(dados[coluna_data]):
        dados[coluna_data] = pd.to_datetime(
            dados[coluna_data], errors="coerce", format="mixed", dayfirst=True
        )
        dados = dados.dropna(subset=[coluna_data])

    if dados.empty:
        return {"erro": "Não existem datas válidas para análise temporal."}

    dados["Periodo"] = (
        dados[coluna_data]
        .dt.to_period("M")
    )

    valores_mensais = (
        dados
        .groupby("Periodo")[coluna_valor]
        .sum()
        .sort_index()
    )

    quantidade_registros = (
        dados
        .groupby("Periodo")
        .size()
    )

    if valores_mensais.empty:
        return {
            "erro": (
                "Não existem dados mensais suficientes."
            )
        }

    # ========================================
    # MELHOR E PIOR MÊS
    # ========================================

    melhor_mes = valores_mensais.idxmax()
    pior_mes = valores_mensais.idxmin()

    # ========================================
    # VARIAÇÃO ENTRE MESES CONSECUTIVOS
    # ========================================

    variacao_mensal = {}

    periodos = list(
        valores_mensais.index
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

        valor_atual = valores_mensais.loc[
            periodo_atual
        ]

        valor_anterior = valores_mensais.loc[
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
                "valor": round(
                    valores_mensais.loc[periodo],
                    2
                ),
                "metrica": metrica,
                "nome_metrica": nome_metrica,
                **({"faturamento": round(valores_mensais.loc[periodo], 2)} if metrica == "faturamento" else {})
            })

    resultado = {
        "metrica": metrica,
        "nome_metrica": nome_metrica,
        "melhor_mes": {
            "periodo": str(melhor_mes),
            "valor": round(valores_mensais.loc[melhor_mes], 2),
            "metrica": metrica,
            "nome_metrica": nome_metrica,
        },
        "pior_mes": {
            "periodo": str(pior_mes),
            "valor": round(valores_mensais.loc[pior_mes], 2),
            "metrica": metrica,
            "nome_metrica": nome_metrica,
        },
        "valores_mensais": {
            str(periodo): round(valor, 2)
            for periodo, valor in valores_mensais.items()
        },
        "variacao_mensal": variacao_mensal,
        "periodos_suspeitos": periodos_suspeitos,
    }
    if metrica == "faturamento":
        resultado["melhor_mes"]["faturamento"] = resultado["melhor_mes"]["valor"]
        resultado["pior_mes"]["faturamento"] = resultado["pior_mes"]["valor"]
        resultado["faturamento_mensal"] = resultado["valores_mensais"]
    return resultado