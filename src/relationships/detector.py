from itertools import combinations

import pandas as pd

from src.analytics.column_mapper import (
    normalizar_nome,
    mapear_colunas
)


LIMITE_UNICIDADE_PK = 0.98
LIMITE_COBERTURA = 60.0
LIMITE_CONFIANCA = 70.0


def remover_plural(
    texto: str
) -> str:

    texto = normalizar_nome(
        texto
    )

    if texto.endswith("oes"):

        return texto[:-3] + "ao"

    if texto.endswith("s"):

        return texto[:-1]

    return texto


def obter_entidade_chave(
    coluna: str
) -> str:

    nome = normalizar_nome(
        coluna
    )

    partes = [
        parte
        for parte in nome.split("_")
        if parte != "id"
    ]

    return "_".join(
        partes
    )


def calcular_afinidade_tabela_chave(
    tabela: str,
    coluna: str
) -> float:

    tabela_norm = remover_plural(
        tabela
    )

    entidade = remover_plural(
        obter_entidade_chave(
            coluna
        )
    )

    if not entidade:
        return 0.0

    if tabela_norm == entidade:
        return 100.0

    if entidade in tabela_norm:
        return 70.0

    if tabela_norm in entidade:
        return 60.0

    return 0.0


def calcular_taxa_unicidade(
    serie: pd.Series
) -> float:

    serie = serie.dropna()

    if len(serie) == 0:
        return 0.0

    return round(
        serie.nunique()
        / len(serie),
        4
    )


def coluna_parece_id(
    coluna: str,
    mapeamento_coluna: dict
) -> bool:

    nome = normalizar_nome(
        coluna
    )

    if (
        nome == "id"
        or nome.endswith("_id")
        or nome.startswith("id_")
    ):
        return True

    return (
        mapeamento_coluna.get(
            "tipo"
        )
        in [
            "identificador",
            "identificador_dimensao"
        ]
    )


def nomes_compativeis(
    coluna_a: str,
    coluna_b: str
) -> bool:

    entidade_a = remover_plural(
        obter_entidade_chave(
            coluna_a
        )
    )

    entidade_b = remover_plural(
        obter_entidade_chave(
            coluna_b
        )
    )

    return (
        entidade_a
        and entidade_b
        and entidade_a == entidade_b
    )


def tipos_compativeis(
    serie_a: pd.Series,
    serie_b: pd.Series
) -> bool:

    if serie_a.dtype == serie_b.dtype:
        return True

    if (
        pd.api.types.is_numeric_dtype(
            serie_a
        )
        and pd.api.types.is_numeric_dtype(
            serie_b
        )
    ):
        return True

    if (
        pd.api.types.is_string_dtype(
            serie_a
        )
        and pd.api.types.is_string_dtype(
            serie_b
        )
    ):
        return True

    return False


def calcular_cobertura(
    serie_fk: pd.Series,
    serie_pk: pd.Series
) -> float:

    valores_fk = set(
        serie_fk
        .dropna()
        .unique()
    )

    valores_pk = set(
        serie_pk
        .dropna()
        .unique()
    )

    if not valores_fk:
        return 0.0

    encontrados = (
        valores_fk
        .intersection(
            valores_pk
        )
    )

    return round(
        len(encontrados)
        / len(valores_fk)
        * 100,
        2
    )


def detectar_relacionamentos(
    tabelas: dict[str, pd.DataFrame]
) -> list:

    relacionamentos = []

    mapeamentos = {
        nome: mapear_colunas(df)
        for nome, df in tabelas.items()
    }

    for tabela_a, tabela_b in combinations(
        tabelas.keys(),
        2
    ):

        df_a = tabelas[
            tabela_a
        ]

        df_b = tabelas[
            tabela_b
        ]

        mapa_a = mapeamentos[
            tabela_a
        ]

        mapa_b = mapeamentos[
            tabela_b
        ]

        for coluna_a in df_a.columns:

            if not coluna_parece_id(
                coluna_a,
                mapa_a[coluna_a]
            ):
                continue

            for coluna_b in df_b.columns:

                if not coluna_parece_id(
                    coluna_b,
                    mapa_b[coluna_b]
                ):
                    continue

                if not nomes_compativeis(
                    coluna_a,
                    coluna_b
                ):
                    continue

                if not tipos_compativeis(
                    df_a[coluna_a],
                    df_b[coluna_b]
                ):
                    continue

                unicidade_a = (
                    calcular_taxa_unicidade(
                        df_a[coluna_a]
                    )
                )

                unicidade_b = (
                    calcular_taxa_unicidade(
                        df_b[coluna_b]
                    )
                )

                a_unica = (
                    unicidade_a
                    >= LIMITE_UNICIDADE_PK
                )

                b_unica = (
                    unicidade_b
                    >= LIMITE_UNICIDADE_PK
                )

                # =================================
                # NENHUM LADO É PK
                # =================================

                if (
                    not a_unica
                    and not b_unica
                ):
                    continue

                # =================================
                # A É PK
                # =================================

                if (
                    a_unica
                    and not b_unica
                ):

                    tabela_pk = tabela_a
                    coluna_pk = coluna_a

                    tabela_fk = tabela_b
                    coluna_fk = coluna_b

                    serie_pk = df_a[
                        coluna_a
                    ]

                    serie_fk = df_b[
                        coluna_b
                    ]

                    tipo = "um_para_muitos"

                # =================================
                # B É PK
                # =================================

                elif (
                    b_unica
                    and not a_unica
                ):

                    tabela_pk = tabela_b
                    coluna_pk = coluna_b

                    tabela_fk = tabela_a
                    coluna_fk = coluna_a

                    serie_pk = df_b[
                        coluna_b
                    ]

                    serie_fk = df_a[
                        coluna_a
                    ]

                    tipo = "um_para_muitos"

                # =================================
                # AMBAS ÚNICAS
                # =================================

                else:

                    valores_a = set(
                        df_a[coluna_a]
                        .dropna()
                        .unique()
                    )

                    valores_b = set(
                        df_b[coluna_b]
                        .dropna()
                        .unique()
                    )

                    menor = min(
                        len(valores_a),
                        len(valores_b)
                    )

                    if menor == 0:
                        continue

                    cobertura = round(
                        len(
                            valores_a.intersection(
                                valores_b
                            )
                        )
                        / menor
                        * 100,
                        2
                    )

                    if cobertura < LIMITE_COBERTURA:
                        continue

                    relacionamentos.append({
                        "tabela_a": tabela_a,
                        "coluna_a": coluna_a,
                        "tabela_b": tabela_b,
                        "coluna_b": coluna_b,

                        "tipo_relacionamento": (
                            "um_para_um"
                        ),

                        "tabela_pk": None,
                        "coluna_pk": None,
                        "tabela_fk": None,
                        "coluna_fk": None,

                        "cobertura": cobertura,
                        "confianca": 90.0,

                        "unicidade_a": unicidade_a,
                        "unicidade_b": unicidade_b
                    })

                    continue

                cobertura = calcular_cobertura(
                    serie_fk,
                    serie_pk
                )

                if cobertura < LIMITE_COBERTURA:
                    continue

                afinidade = (
                    calcular_afinidade_tabela_chave(
                        tabela_pk,
                        coluna_pk
                    )
                )

                # =================================
                # SCORE
                # =================================

                confianca = (
                    30
                    + cobertura * 0.40
                    + afinidade * 0.30
                )

                confianca = round(
                    min(
                        confianca,
                        100
                    ),
                    2
                )

                if confianca < LIMITE_CONFIANCA:
                    continue

                relacionamentos.append({
                    "tabela_a": tabela_a,
                    "coluna_a": coluna_a,
                    "tabela_b": tabela_b,
                    "coluna_b": coluna_b,

                    "tipo_relacionamento": tipo,

                    "tabela_pk": tabela_pk,
                    "coluna_pk": coluna_pk,

                    "tabela_fk": tabela_fk,
                    "coluna_fk": coluna_fk,

                    "cobertura": cobertura,
                    "confianca": confianca,

                    "afinidade_pk": afinidade,

                    "unicidade_a": unicidade_a,
                    "unicidade_b": unicidade_b
                })

    relacionamentos.sort(
        key=lambda item: (
            item[
                "tipo_relacionamento"
            ]
            != "um_para_muitos",

            -item[
                "confianca"
            ]
        )
    )

    return relacionamentos