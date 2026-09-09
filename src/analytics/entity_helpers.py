import pandas as pd


def criar_mapa_rotulos(
    df: pd.DataFrame,
    coluna_id: str,
    coluna_rotulo: str | None
) -> dict:
    """
    Cria um mapa:

    ID -> Nome

    O agrupamento continua sendo feito pelo ID.
    O nome serve somente para exibição.
    """

    if not coluna_rotulo:
        return {}

    dados = (
        df[
            [
                coluna_id,
                coluna_rotulo
            ]
        ]
        .dropna(
            subset=[coluna_id]
        )
        .copy()
    )

    if dados.empty:
        return {}

    mapa = {}

    for identificador, grupo in dados.groupby(
        coluna_id
    ):

        valores = (
            grupo[coluna_rotulo]
            .dropna()
            .astype(str)
        )

        if valores.empty:
            continue

        mapa[
            identificador
        ] = valores.iloc[0]

    return mapa


def formatar_entidade(
    identificador,
    mapa_rotulos: dict
) -> str:
    """
    Exemplo:

    Modi (ID 541)

    Se não houver nome:
    541
    """

    rotulo = mapa_rotulos.get(
        identificador
    )

    if (
        rotulo is None
        or str(rotulo).strip() == ""
    ):

        return str(
            identificador
        )

    return (
        f"{rotulo} "
        f"(ID {identificador})"
    )


def preparar_entidade(
    df: pd.DataFrame,
    coluna_id: str | None,
    coluna_rotulo: str | None
):
    """
    Define qual coluna será realmente usada
    para agrupamento.

    Prioridade:
    1. ID
    2. nome/rotulo
    """

    if coluna_id:

        mapa = criar_mapa_rotulos(
            df,
            coluna_id,
            coluna_rotulo
        )

        return (
            coluna_id,
            mapa
        )

    if coluna_rotulo:

        return (
            coluna_rotulo,
            {}
        )

    return (
        None,
        {}
    )