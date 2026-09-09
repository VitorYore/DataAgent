import pandas as pd

from src.etl.transformation_log import TransformationLog


def preencher_colunas_temporais(
    df: pd.DataFrame,
    log: TransformationLog
) -> pd.DataFrame:

    df_tratado = df.copy()

    if "Data" not in df_tratado.columns:
        return df_tratado

    if not pd.api.types.is_datetime64_any_dtype(
        df_tratado["Data"]
    ):
        return df_tratado

    colunas_temporais = {
        "Ano": "year",
        "Mês": "month",
        "Trimestre": "quarter"
    }

    for coluna, atributo in colunas_temporais.items():

        if coluna not in df_tratado.columns:
            continue

        nulos_antes = df_tratado[coluna].isna().sum()

        mascara = (
            df_tratado[coluna].isna()
            & df_tratado["Data"].notna()
        )

        if atributo == "year":
            valores = df_tratado.loc[
                mascara,
                "Data"
            ].dt.year

        elif atributo == "month":
            valores = df_tratado.loc[
                mascara,
                "Data"
            ].dt.month

        elif atributo == "quarter":
            valores = df_tratado.loc[
                mascara,
                "Data"
            ].dt.quarter

        df_tratado.loc[
            mascara,
            coluna
        ] = valores

        preenchidos = int(mascara.sum())

        if preenchidos > 0:
            log.adicionar(
                coluna=coluna,
                tipo_transformacao="preenchimento_nulo",
                antes=f"{nulos_antes} nulos",
                depois=(
                    f"{df_tratado[coluna].isna().sum()} nulos"
                ),
                detalhes=(
                    f"{preenchidos} valores preenchidos "
                    "a partir da coluna Data."
                )
            )

    return df_tratado


def preencher_lucro(
    df: pd.DataFrame,
    log: TransformationLog
) -> pd.DataFrame:

    df_tratado = df.copy()

    colunas_necessarias = [
        "Lucro",
        "Valor_liquido",
        "Total_custo"
    ]

    for coluna in colunas_necessarias:
        if coluna not in df_tratado.columns:
            return df_tratado

    nulos_antes = df_tratado["Lucro"].isna().sum()

    mascara = (
        df_tratado["Lucro"].isna()
        & df_tratado["Valor_liquido"].notna()
        & df_tratado["Total_custo"].notna()
    )

    df_tratado.loc[
        mascara,
        "Lucro"
    ] = (
        df_tratado.loc[mascara, "Valor_liquido"]
        - df_tratado.loc[mascara, "Total_custo"]
    )

    preenchidos = int(mascara.sum())

    if preenchidos > 0:
        log.adicionar(
            coluna="Lucro",
            tipo_transformacao="recalculo_valor_nulo",
            antes=f"{nulos_antes} nulos",
            depois=(
                f"{df_tratado['Lucro'].isna().sum()} nulos"
            ),
            detalhes=(
                f"{preenchidos} valores recalculados usando "
                "Valor_liquido - Total_custo."
            )
        )

    return df_tratado


def registrar_nulos_nao_tratados(
    df: pd.DataFrame,
    log: TransformationLog
) -> None:

    motivos = {
    "Data": (
        "Não existe informação confiável "
        "para reconstruir a data."
    ),

    "Lucro": (
        "A regra original de cálculo "
        "do lucro não é conhecida."
    ),

    "Percentual_lucro": (
        "A regra original de cálculo "
        "não é conhecida."
    ),

    "Ano": (
        "Não foi possível preencher "
        "porque a Data também está ausente."
    ),

    "Mês": (
        "Não foi possível preencher "
        "porque a Data também está ausente."
    ),

    "Nome_mes": (
        "Não foi possível preencher "
        "porque a Data também está ausente."
    ),

    "Trimestre": (
        "Não foi possível preencher "
        "porque a Data também está ausente."
    )
}

    for coluna, motivo in motivos.items():

        if coluna not in df.columns:
            continue

        quantidade = int(
            df[coluna].isna().sum()
        )

        if quantidade > 0:
            log.adicionar(
                coluna=coluna,
                tipo_transformacao="nulo_nao_tratado",
                antes=f"{quantidade} nulos",
                depois=f"{quantidade} nulos",
                detalhes=motivo
            )


def tratar_nulos(
    df: pd.DataFrame,
    log: TransformationLog
) -> pd.DataFrame:

    df_tratado = preencher_colunas_temporais(
        df,
        log
    )

    registrar_nulos_nao_tratados(
        df_tratado,
        log
    )

    return df_tratado