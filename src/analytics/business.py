import pandas as pd

from src.analytics.column_mapper import (
    mapear_colunas
)


def encontrar_coluna_por_papel(
    mapeamento: dict,
    papel: str
):

    candidatos = []

    for coluna, dados in (
        mapeamento.items()
    ):

        if dados.get(
            "papel"
        ) != papel:

            continue

        candidatos.append({
            "coluna": coluna,
            "confianca": dados.get(
                "confianca",
                0
            )
        })

    if not candidatos:

        return None

    candidatos.sort(
        key=lambda item: item[
            "confianca"
        ],
        reverse=True
    )

    return candidatos[0][
        "coluna"
    ]


def calcular_kpis(
    df: pd.DataFrame
) -> dict:

    mapeamento = mapear_colunas(
        df
    )

    coluna_faturamento = (
        encontrar_coluna_por_papel(
            mapeamento,
            "faturamento"
        )
    )

    coluna_custo = (
        encontrar_coluna_por_papel(
            mapeamento,
            "custo"
        )
    )

    coluna_lucro = (
        encontrar_coluna_por_papel(
            mapeamento,
            "lucro"
        )
    )

    coluna_quantidade = (
        encontrar_coluna_por_papel(
            mapeamento,
            "quantidade"
        )
    )

    coluna_venda = (
        encontrar_coluna_por_papel(
            mapeamento,
            "venda_id"
        )
    )

    if not coluna_venda:

        coluna_venda = (
            encontrar_coluna_por_papel(
                mapeamento,
                "pedido"
            )
        )

    resultado = {}

    # ========================================
    # FATURAMENTO
    # ========================================

    faturamento = None

    if coluna_faturamento:

        faturamento = (
            df[coluna_faturamento]
            .sum()
        )

        resultado[
            "faturamento_total"
        ] = round(
            float(faturamento),
            2
        )

    # ========================================
    # CUSTO
    # ========================================

    custo = None

    if coluna_custo:

        custo = (
            df[coluna_custo]
            .sum()
        )

        resultado[
            "custo_total"
        ] = round(
            float(custo),
            2
        )

    # ========================================
    # LUCRO
    # ========================================

    lucro = None

    if coluna_lucro:

        lucro = (
            df[coluna_lucro]
            .sum()
        )

        resultado[
            "lucro_total"
        ] = round(
            float(lucro),
            2
        )

    # ========================================
    # QUANTIDADE VENDIDA
    # ========================================

    if coluna_quantidade:

        quantidade = (
            df[coluna_quantidade]
            .sum()
        )

        resultado[
            "quantidade_vendida"
        ] = round(
            float(quantidade),
            2
        )

    # ========================================
    # QUANTIDADE DE VENDAS / PEDIDOS
    # ========================================

    if coluna_venda:

        quantidade_vendas = (
            df[coluna_venda]
            .nunique()
        )

        resultado[
            "quantidade_pedidos"
        ] = int(
            quantidade_vendas
        )

        # ====================================
        # TICKET MÉDIO
        # ====================================

        if (
            faturamento is not None
            and quantidade_vendas > 0
        ):

            ticket_medio = (
                faturamento
                / quantidade_vendas
            )

            resultado[
                "ticket_medio"
            ] = round(
                float(ticket_medio),
                2
            )

    # ========================================
    # MARGEM
    # ========================================

    if (
        lucro is not None
        and faturamento is not None
        and faturamento != 0
    ):

        margem = (
            lucro
            / faturamento
            * 100
        )

        resultado[
            "margem_lucro"
        ] = round(
            float(margem),
            2
        )

    return resultado