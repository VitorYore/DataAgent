import pandas as pd

from src.quality.type_inference import normalizar_numero
from src.etl.transformation_log import TransformationLog
from src.etl.null_handler import tratar_nulos


def converter_colunas_numericas(
    df: pd.DataFrame,
    colunas: list[str],
    log: TransformationLog
) -> pd.DataFrame:

    df_tratado = df.copy()

    for coluna in colunas:
        tipo_antes = str(df_tratado[coluna].dtype)
        serie_normalizada = df_tratado[coluna].apply(normalizar_numero)
        convertido = pd.to_numeric(serie_normalizada, errors="coerce")
        novos_nulos = int(convertido.isna().sum() - df_tratado[coluna].isna().sum())
        valores_origem = int(df_tratado[coluna].notna().sum())
        proporcao_convertida = float(convertido.notna().sum() / max(1, valores_origem))

        if novos_nulos > 0 and proporcao_convertida < 0.95:
            log.adicionar(
                coluna=coluna,
                tipo_transformacao="conversao_numerica_cancelada",
                antes=tipo_antes,
                depois=tipo_antes,
                detalhes=(
                    f"Conversão cancelada: somente {proporcao_convertida:.2%} dos valores não nulos "
                    f"puderam ser interpretados como números; {novos_nulos} valores foram preservados sem conversão."
                )
            )
            continue

        df_tratado[coluna] = convertido
        if novos_nulos:
            log.adicionar(
                coluna=coluna,
                tipo_transformacao="conversao_numerica_parcial",
                antes=tipo_antes,
                depois=str(df_tratado[coluna].dtype),
                detalhes=(
                    f"Conversão realizada com {proporcao_convertida:.2%} de confiança; {novos_nulos} valores "
                    "não numéricos ficaram nulos no dataset analítico. Os dados originais permanecem preservados."
                )
            )
        else:
            log.adicionar(
                coluna=coluna,
                tipo_transformacao="conversao_numerica",
                antes=tipo_antes,
                depois=str(df_tratado[coluna].dtype),
                detalhes="Conversão realizada com sucesso."
            )

    return df_tratado


def converter_colunas_data(
    df: pd.DataFrame,
    colunas: list[str],
    log: TransformationLog
) -> pd.DataFrame:

    df_tratado = df.copy()

    for coluna in colunas:
        tipo_antes = str(df_tratado[coluna].dtype)

        convertido = pd.to_datetime(
            df_tratado[coluna],
            errors="coerce",
            format="mixed",
            dayfirst=True
        )

        novos_nulos = (
            convertido.isna().sum()
            - df_tratado[coluna].isna().sum()
        )

        if novos_nulos > 0:
            log.adicionar(
                coluna=coluna,
                tipo_transformacao="conversao_data_cancelada",
                antes=tipo_antes,
                depois=tipo_antes,
                detalhes=(
                    f"A conversão geraria {novos_nulos} "
                    "novos valores nulos."
                )
            )

            continue

        df_tratado[coluna] = convertido

        log.adicionar(
            coluna=coluna,
            tipo_transformacao="conversao_data",
            antes=tipo_antes,
            depois=str(df_tratado[coluna].dtype),
            detalhes="Conversão realizada com sucesso."
        )

    return df_tratado


def executar_etl(
    df: pd.DataFrame,
    diagnostico: dict
):
    log = TransformationLog()

    inferencia = diagnostico["inferencia_tipos"]

    colunas_numericas = list(
        inferencia["possiveis_numeros"].keys()
    )

    colunas_data = list(
        inferencia["possiveis_datas"].keys()
    )

    # ========================================
    # 1. CONVERSÃO DE COLUNAS NUMÉRICAS
    # ========================================

    df_tratado = converter_colunas_numericas(
        df,
        colunas_numericas,
        log
    )

    # ========================================
    # 2. CONVERSÃO DE COLUNAS DE DATA
    # ========================================

    df_tratado = converter_colunas_data(
        df_tratado,
        colunas_data,
        log
    )

    # ========================================
    # 3. TRATAMENTO DOS VALORES NULOS
    # ========================================

    df_tratado = tratar_nulos(
        df_tratado,
        log
    )

    return df_tratado, log.obter_logs()