import re

import pandas as pd


def normalizar_nome_coluna(nome_coluna) -> str:
    return str(nome_coluna).lower().strip()


def normalizar_numero(valor):
    if pd.isna(valor):
        return None

    valor = str(valor).strip()

    # Remove símbolos comuns
    valor = valor.replace("R$", "")
    valor = valor.replace("%", "")
    valor = valor.replace(" ", "")

    # Formato brasileiro:
    # 1.250,90 -> 1250.90
    if "," in valor and "." in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    # 128,70 -> 128.70
    elif "," in valor:
        valor = valor.replace(",", ".")

    return valor


def detectar_possivel_data(
    nome_coluna,
    serie: pd.Series
) -> tuple[bool, float]:

    if (
        serie.dtype != "object"
        and not pd.api.types.is_string_dtype(serie.dtype)
    ):
        return False, 0.0

    nomes_data = [
        "data",
        "date",
        "dt",
        "nascimento",
        "vencimento"
    ]

    nome = normalizar_nome_coluna(nome_coluna)

    nome_sugere_data = any(
        termo in nome
        for termo in nomes_data
    )

    amostra = serie.dropna().astype(str).str.strip()

    if amostra.empty:
        return False, 0.0

    # Verifica formatos comuns antes da conversão
    padrao_data = amostra.str.match(
        r"^\d{4}-\d{1,2}-\d{1,2}$"
        r"|^\d{1,2}/\d{1,2}/\d{4}$"
    )

    percentual_padrao = padrao_data.mean()

    if not nome_sugere_data and percentual_padrao < 0.80:
        return False, 0.0

    convertido = pd.to_datetime(
        amostra,
        errors="coerce",
        format="mixed",
        dayfirst=True
    )

    confianca = convertido.notna().mean()

    return (
        confianca >= 0.80,
        round(float(confianca * 100), 2)
    )


def detectar_possivel_numero(
    nome_coluna,
    serie: pd.Series
) -> tuple[bool, float]:

    if (
        serie.dtype != "object"
        and not pd.api.types.is_string_dtype(serie.dtype)
    ):
        return False, 0.0

    amostra = serie.dropna()

    if amostra.empty:
        return False, 0.0

    valores_normalizados = amostra.apply(
        normalizar_numero
    )

    convertido = pd.to_numeric(
        valores_normalizados,
        errors="coerce"
    )

    confianca = convertido.notna().mean()

    return (
        confianca >= 0.80,
        round(float(confianca * 100), 2)
    )


def detectar_identificador(
    nome_coluna,
    serie: pd.Series
) -> tuple[bool, float]:

    termos_identificador = {
        "id",
        "codigo",
        "cod",
        "pedido",
        "transacao",
        "transaction"
    }

    nome = normalizar_nome_coluna(nome_coluna)

    # Divide nomes como:
    # cliente_id -> ["cliente", "id"]
    # id_cliente -> ["id", "cliente"]
    partes_nome = re.split(r"[_\-\s]+", nome)

    nome_sugere_id = any(
        parte in termos_identificador
        for parte in partes_nome
    )

    amostra = serie.dropna().astype(str).str.strip()

    if amostra.empty:
        return False, 0.0

    possui_letras = amostra.str.contains(
        r"[A-Za-z]",
        regex=True
    ).mean()

    proporcao_unicos = (
        amostra.nunique()
        / len(amostra)
    )

    confianca = 0.0

    if nome_sugere_id:
        confianca += 60

    if possui_letras > 0:
        confianca += 20

    if proporcao_unicos >= 0.70:
        confianca += 20

    return (
        confianca >= 60,
        round(confianca, 2)
    )


def inferir_tipos(df: pd.DataFrame) -> dict:
    possiveis_datas = {}
    possiveis_numeros = {}
    identificadores = {}

    for coluna in df.columns:
        serie = df[coluna]

        eh_id, confianca_id = detectar_identificador(
            coluna,
            serie
        )

        if eh_id:
            identificadores[str(coluna)] = {
                "tipo_atual": str(serie.dtype),
                "tipo_sugerido": "identificador",
                "confianca": confianca_id
            }

            continue

        eh_data, confianca_data = detectar_possivel_data(
            coluna,
            serie
        )

        if eh_data:
            possiveis_datas[str(coluna)] = {
                "tipo_atual": str(serie.dtype),
                "tipo_sugerido": "datetime",
                "confianca": confianca_data
            }

            continue

        eh_numero, confianca_numero = detectar_possivel_numero(
            coluna,
            serie
        )

        if eh_numero:
            possiveis_numeros[str(coluna)] = {
                "tipo_atual": str(serie.dtype),
                "tipo_sugerido": "numerico",
                "confianca": confianca_numero
            }

    return {
        "identificadores": identificadores,
        "possiveis_datas": possiveis_datas,
        "possiveis_numeros": possiveis_numeros
    }