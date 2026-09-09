import pandas as pd

from src.analytics.column_mapper import (
    mapear_colunas
)

from src.analytics.business import (
    encontrar_coluna_por_papel
)


def criar_faturamento(
    df: pd.DataFrame,
    mapeamento: dict
):

    if encontrar_coluna_por_papel(
        mapeamento,
        "faturamento"
    ):

        return df, None

    coluna_quantidade = (
        encontrar_coluna_por_papel(
            mapeamento,
            "quantidade"
        )
    )

    coluna_preco = (
        encontrar_coluna_por_papel(
            mapeamento,
            "preco_unitario"
        )
    )

    if (
        not coluna_quantidade
        or not coluna_preco
    ):

        return df, None

    df[
        "Faturamento_Calculado"
    ] = (
        df[coluna_quantidade]
        * df[coluna_preco]
    )

    return df, {
        "metrica": "faturamento",
        "coluna_criada": (
            "Faturamento_Calculado"
        ),
        "formula": (
            f"{coluna_quantidade} * "
            f"{coluna_preco}"
        ),
        "origem": "derivada"
    }


def criar_custo_total(
    df: pd.DataFrame,
    mapeamento: dict
):

    if encontrar_coluna_por_papel(
        mapeamento,
        "custo"
    ):

        return df, None

    coluna_quantidade = (
        encontrar_coluna_por_papel(
            mapeamento,
            "quantidade"
        )
    )

    coluna_custo_unitario = (
        encontrar_coluna_por_papel(
            mapeamento,
            "custo_unitario"
        )
    )

    if (
        not coluna_quantidade
        or not coluna_custo_unitario
    ):

        return df, None

    df[
        "Custo_Total_Calculado"
    ] = (
        df[coluna_quantidade]
        * df[coluna_custo_unitario]
    )

    return df, {
        "metrica": "custo",
        "coluna_criada": (
            "Custo_Total_Calculado"
        ),
        "formula": (
            f"{coluna_quantidade} * "
            f"{coluna_custo_unitario}"
        ),
        "origem": "derivada"
    }


def criar_lucro(
    df: pd.DataFrame,
    mapeamento: dict
):

    if encontrar_coluna_por_papel(
        mapeamento,
        "lucro"
    ):

        return df, None

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

    if (
        not coluna_faturamento
        or not coluna_custo
    ):

        return df, None

    df[
        "Lucro_Calculado"
    ] = (
        df[coluna_faturamento]
        - df[coluna_custo]
    )

    return df, {
        "metrica": "lucro",
        "coluna_criada": (
            "Lucro_Calculado"
        ),
        "formula": (
            f"{coluna_faturamento} - "
            f"{coluna_custo}"
        ),
        "origem": "derivada"
    }


def criar_margem_lucro(
    df: pd.DataFrame,
    mapeamento: dict
):

    if encontrar_coluna_por_papel(
        mapeamento,
        "margem_lucro"
    ):

        return df, None

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

    if (
        not coluna_faturamento
        or not coluna_lucro
    ):

        return df, None

    faturamento = df[
        coluna_faturamento
    ]

    lucro = df[
        coluna_lucro
    ]

    df[
        "Margem_Lucro_Calculada"
    ] = 0.0

    mascara = (
        faturamento != 0
    )

    df.loc[
        mascara,
        "Margem_Lucro_Calculada"
    ] = (
        lucro[mascara]
        / faturamento[mascara]
        * 100
    )

    return df, {
        "metrica": "margem_lucro",
        "coluna_criada": (
            "Margem_Lucro_Calculada"
        ),
        "formula": (
            f"{coluna_lucro} / "
            f"{coluna_faturamento} * 100"
        ),
        "origem": "derivada"
    }


def criar_metricas_derivadas(
    df: pd.DataFrame
):

    df = df.copy()

    logs = []

    # ========================================
    # FATURAMENTO
    # ========================================

    mapeamento = mapear_colunas(
        df
    )

    df, log = criar_faturamento(
        df,
        mapeamento
    )

    if log:
        logs.append(log)

    # ========================================
    # CUSTO
    # Recalcula mapper porque uma coluna
    # pode ter acabado de ser criada.
    # ========================================

    mapeamento = mapear_colunas(
        df
    )

    df, log = criar_custo_total(
        df,
        mapeamento
    )

    if log:
        logs.append(log)

    # ========================================
    # LUCRO
    # ========================================

    mapeamento = mapear_colunas(
        df
    )

    df, log = criar_lucro(
        df,
        mapeamento
    )

    if log:
        logs.append(log)

    # ========================================
    # MARGEM
    # ========================================

    mapeamento = mapear_colunas(
        df
    )

    df, log = criar_margem_lucro(
        df,
        mapeamento
    )

    if log:
        logs.append(log)

    return df, logs