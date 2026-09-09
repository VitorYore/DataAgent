import pandas as pd

from src.analytics.column_mapper import (
    normalizar_nome
)


TABELAS_TRANSACIONAIS = [
    "venda",
    "vendas",
    "historico_vendas",
    "devolucao",
    "devolucoes",
    "pedido",
    "pedidos",
    "pedidos_compra",
    "campanha",
    "campanhas",
    "custo_operacional",
    "custos_operacionais",
    "satisfacao",
    "avaliacao",
    "avaliacoes"
]


def nome_parece_transacional(
    nome_tabela: str
) -> bool:

    nome = normalizar_nome(
        nome_tabela
    )

    return any(
        termo in nome
        for termo in TABELAS_TRANSACIONAIS
    )


def entidade_da_chave(
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

    entidade = "_".join(
        partes
    )

    if entidade.endswith("s"):
        entidade = entidade[:-1]

    return entidade


def calcular_score_dimensao(
    tabela: str,
    coluna_pk: str,
    relacionamento: dict
) -> float:

    score = relacionamento.get(
        "confianca",
        0
    )

    nome_tabela = normalizar_nome(
        tabela
    )

    entidade = entidade_da_chave(
        coluna_pk
    )

    # ========================================
    # TABELA COM NOME DA ENTIDADE
    # ========================================

    if (
        entidade
        and entidade in nome_tabela
    ):

        score += 50

    # ========================================
    # DIMENSÕES TRANSAÇÃO/LOG
    # RECEBEM GRANDE PENALIDADE
    # ========================================

    if nome_parece_transacional(
        tabela
    ):

        score -= 100

    return score


def contar_fks(
    tabela: str,
    relacionamentos: list
) -> int:

    return sum(
        1
        for relacionamento in relacionamentos
        if (
            relacionamento.get(
                "tipo_relacionamento"
            )
            == "um_para_muitos"
            and relacionamento.get(
                "tabela_fk"
            )
            == tabela
        )
    )


def escolher_tabela_principal(
    tabelas: dict[str, pd.DataFrame],
    relacionamentos: list
) -> str:

    scores = {}

    for nome, df in tabelas.items():

        score = len(
            df
        )

        score += (
            contar_fks(
                nome,
                relacionamentos
            )
            * 10000
        )

        nome_normalizado = (
            normalizar_nome(
                nome
            )
        )

        if nome_normalizado in [
            "vendas",
            "sales",
            "transacoes",
            "transactions"
        ]:

            score += 20000

        if "historico" in nome_normalizado:

            score -= 5000

        scores[
            nome
        ] = score

    return max(
        scores,
        key=scores.get
    )


def preparar_dimensao_para_merge(
    df: pd.DataFrame,
    coluna_pk: str,
    nome_tabela: str
) -> pd.DataFrame:

    df = df.copy()

    renomear = {}

    for coluna in df.columns:

        if coluna == coluna_pk:
            continue

        renomear[
            coluna
        ] = (
            f"{nome_tabela}__{coluna}"
        )

    return df.rename(
        columns=renomear
    )


def validar_pk(
    df: pd.DataFrame,
    coluna_pk: str
) -> bool:

    serie = df[
        coluna_pk
    ].dropna()

    if serie.empty:
        return False

    return (
        serie.nunique()
        == len(serie)
    )


def selecionar_melhores_dimensoes(
    tabela_base: str,
    relacionamentos: list
) -> list:

    """
    Para cada FK da tabela fato,
    escolhe apenas a melhor tabela PK.
    """

    candidatos_por_fk = {}

    for relacionamento in relacionamentos:

        if (
            relacionamento.get(
                "tipo_relacionamento"
            )
            != "um_para_muitos"
        ):
            continue

        if (
            relacionamento.get(
                "tabela_fk"
            )
            != tabela_base
        ):
            continue

        coluna_fk = relacionamento[
            "coluna_fk"
        ]

        tabela_pk = relacionamento[
            "tabela_pk"
        ]

        coluna_pk = relacionamento[
            "coluna_pk"
        ]

        score = calcular_score_dimensao(
            tabela_pk,
            coluna_pk,
            relacionamento
        )

        candidato = {
            **relacionamento,
            "score_dimensao": score
        }

        if coluna_fk not in candidatos_por_fk:

            candidatos_por_fk[
                coluna_fk
            ] = candidato

            continue

        atual = candidatos_por_fk[
            coluna_fk
        ]

        if (
            candidato[
                "score_dimensao"
            ]
            > atual[
                "score_dimensao"
            ]
        ):

            candidatos_por_fk[
                coluna_fk
            ] = candidato

    selecionados = list(
        candidatos_por_fk.values()
    )

    selecionados.sort(
        key=lambda item: (
            item[
                "score_dimensao"
            ]
        ),
        reverse=True
    )

    return selecionados


def executar_merge(
    df_base: pd.DataFrame,
    df_dimensao: pd.DataFrame,
    coluna_fk: str,
    coluna_pk: str,
    nome_dimensao: str
):

    if not validar_pk(
        df_dimensao,
        coluna_pk
    ):

        raise ValueError(
            f"{nome_dimensao}.{coluna_pk} "
            "não é uma PK única."
        )

    dimensao = (
        preparar_dimensao_para_merge(
            df_dimensao,
            coluna_pk,
            nome_dimensao
        )
    )

    linhas_antes = len(
        df_base
    )

    resultado = pd.merge(
        df_base,
        dimensao,
        how="left",
        left_on=coluna_fk,
        right_on=coluna_pk,
        validate="many_to_one"
    )

    linhas_depois = len(
        resultado
    )

    if linhas_depois != linhas_antes:

        raise ValueError(
            "O merge alterou a quantidade "
            f"de linhas de {linhas_antes} "
            f"para {linhas_depois}."
        )

    if (
        coluna_pk != coluna_fk
        and coluna_pk in resultado.columns
    ):

        resultado = resultado.drop(
            columns=[
                coluna_pk
            ]
        )

    return resultado


def criar_dataset_analitico(
    tabelas: dict[str, pd.DataFrame],
    relacionamentos: list,
    tabela_principal: str | None = None
):

    if tabela_principal is None:

        tabela_principal = (
            escolher_tabela_principal(
                tabelas,
                relacionamentos
            )
        )

    if tabela_principal not in tabelas:

        raise ValueError(
            f"Tabela principal "
            f"'{tabela_principal}' "
            "não encontrada."
        )

    df_analitico = (
        tabelas[
            tabela_principal
        ].copy()
    )

    logs = []

    relacionamentos_selecionados = (
        selecionar_melhores_dimensoes(
            tabela_principal,
            relacionamentos
        )
    )

    tabelas_adicionadas = set()

    for relacionamento in (
        relacionamentos_selecionados
    ):

        tabela_dimensao = (
            relacionamento[
                "tabela_pk"
            ]
        )

        coluna_pk = (
            relacionamento[
                "coluna_pk"
            ]
        )

        coluna_fk = (
            relacionamento[
                "coluna_fk"
            ]
        )

        # ========================================
        # NÃO JUNTAR TABELA TRANSACIONAL
        # COMO DIMENSÃO
        # ========================================

        if nome_parece_transacional(
            tabela_dimensao
        ):

            logs.append({
                "status": "ignorado",
                "tabela_base": tabela_principal,
                "tabela_adicionada": tabela_dimensao,
                "coluna_fk": coluna_fk,
                "coluna_pk": coluna_pk,
                "motivo": (
                    "Tabela classificada como "
                    "transacional/auxiliar."
                )
            })

            continue

        if tabela_dimensao in (
            tabelas_adicionadas
        ):
            continue

        df_dimensao = tabelas[
            tabela_dimensao
        ]

        colunas_antes = len(
            df_analitico.columns
        )

        try:

            df_analitico = executar_merge(
                df_analitico,
                df_dimensao,
                coluna_fk,
                coluna_pk,
                tabela_dimensao
            )

            colunas_depois = len(
                df_analitico.columns
            )

            tabelas_adicionadas.add(
                tabela_dimensao
            )

            logs.append({
                "status": "sucesso",
                "tabela_base": tabela_principal,
                "tabela_adicionada": tabela_dimensao,

                "coluna_fk": coluna_fk,
                "coluna_pk": coluna_pk,

                "confianca": (
                    relacionamento[
                        "confianca"
                    ]
                ),

                "cobertura": (
                    relacionamento[
                        "cobertura"
                    ]
                ),

                "score_dimensao": (
                    relacionamento[
                        "score_dimensao"
                    ]
                ),

                "colunas_adicionadas": (
                    colunas_depois
                    - colunas_antes
                ),

                "linhas_resultado": len(
                    df_analitico
                )
            })

        except Exception as erro:

            logs.append({
                "status": "ignorado",
                "tabela_base": tabela_principal,
                "tabela_adicionada": tabela_dimensao,
                "coluna_fk": coluna_fk,
                "coluna_pk": coluna_pk,
                "motivo": str(
                    erro
                )
            })

    return (
        df_analitico,
        tabela_principal,
        logs
    )