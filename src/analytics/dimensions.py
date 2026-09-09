import pandas as pd

from src.analytics.column_mapper import (
    mapear_colunas
)

from src.analytics.business import (
    encontrar_coluna_por_papel
)

from src.analytics.entity_helpers import (
    preparar_entidade,
    formatar_entidade
)


CONFIG_DIMENSOES = {

    "produto": {
        "id": "produto_id",
        "rotulo": "produto"
    },

    "categoria": {
        "papel": "categoria"
    },

    "loja": {
        "id": "loja_id",
        "rotulo": "loja"
    },

    "regiao": {
        "papel": "regiao"
    },

    "cidade_cliente": {
        "papel": "cidade_cliente"
    },

    "cidade_loja": {
        "papel": "cidade_loja"
    },

    "colaborador": {
        "id": "colaborador_id",
        "rotulo": "colaborador"
    },

    "canal_venda": {
        "papel": "canal_venda"
    },

    "canal_compra": {
        "papel": "canal_compra"
    },

    "tipo_loja": {
        "papel": "tipo_loja"
    },

    "funcao_colaborador": {
        "papel": "funcao_colaborador"
    },

    "genero_cliente": {
        "papel": "genero_cliente"
    },

    "cor_produto": {
        "papel": "cor_produto"
    },

    "tamanho_produto": {
        "papel": "tamanho_produto"
    }
}


def calcular_participacao(
    serie: pd.Series,
    mapa_rotulos: dict
) -> list:

    total = serie.sum()

    if total == 0:
        return []

    resultado = []

    for valor, quantidade in (
        serie
        .sort_values(
            ascending=False
        )
        .head(5)
        .items()
    ):

        resultado.append({
            "valor": (
                formatar_entidade(
                    valor,
                    mapa_rotulos
                )
            ),
            "id": valor,
            "participacao": round(
                float(
                    quantidade
                    / total
                    * 100
                ),
                2
            )
        })

    return resultado


def analisar_dimensao(
    df: pd.DataFrame,
    nome_dimensao: str,
    coluna_agrupamento: str,
    mapa_rotulos: dict,
    coluna_faturamento: str | None,
    coluna_lucro: str | None,
    coluna_quantidade: str | None
) -> dict:

    resultado = {
        "coluna": coluna_agrupamento,
        "papel": nome_dimensao,
        "quantidade_valores": int(
            df[coluna_agrupamento]
            .dropna()
            .nunique()
        )
    }

    faturamento = None
    quantidade = None

    # ========================================
    # FATURAMENTO
    # ========================================

    if coluna_faturamento:

        faturamento = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[coluna_faturamento]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "top_faturamento"
        ] = [
            {
                "valor": (
                    formatar_entidade(
                        valor,
                        mapa_rotulos
                    )
                ),
                "id": valor,
                "faturamento": round(
                    float(total),
                    2
                )
            }
            for valor, total
            in faturamento.head(5).items()
        ]

        resultado[
            "participacao_faturamento"
        ] = calcular_participacao(
            faturamento,
            mapa_rotulos
        )

    # ========================================
    # QUANTIDADE
    # ========================================

    if coluna_quantidade:

        quantidade = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[coluna_quantidade]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "mais_vendidos"
        ] = [
            {
                "valor": (
                    formatar_entidade(
                        valor,
                        mapa_rotulos
                    )
                ),
                "id": valor,
                "quantidade": round(
                    float(total),
                    2
                )
            }
            for valor, total
            in quantidade.head(5).items()
        ]

        resultado[
            "participacao_volume"
        ] = calcular_participacao(
            quantidade,
            mapa_rotulos
        )

    # ========================================
    # VALOR MÉDIO
    # ========================================

    if (
        faturamento is not None
        and quantidade is not None
    ):

        resumo = pd.DataFrame({
            "faturamento": faturamento,
            "quantidade": quantidade
        }).fillna(0)

        resumo[
            "valor_medio_unidade"
        ] = resumo.apply(
            lambda linha: (
                linha["faturamento"]
                / linha["quantidade"]
                if linha["quantidade"] > 0
                else 0
            ),
            axis=1
        )

        valor_medio = (
            resumo[
                "valor_medio_unidade"
            ]
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "top_valor_medio_unidade"
        ] = [
            {
                "valor": (
                    formatar_entidade(
                        valor,
                        mapa_rotulos
                    )
                ),
                "id": valor,
                "valor_medio_unidade": round(
                    float(media),
                    2
                )
            }
            for valor, media
            in valor_medio.head(5).items()
        ]

    # ========================================
    # LUCRO
    # ========================================

    if coluna_lucro:

        lucro = (
            df
            .dropna(
                subset=[
                    coluna_agrupamento
                ]
            )
            .groupby(
                coluna_agrupamento
            )[coluna_lucro]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        resultado[
            "top_lucro"
        ] = [
            {
                "valor": (
                    formatar_entidade(
                        valor,
                        mapa_rotulos
                    )
                ),
                "id": valor,
                "lucro": round(
                    float(total),
                    2
                )
            }
            for valor, total
            in lucro.head(5).items()
        ]

        negativos = lucro[
            lucro < 0
        ]

        resultado[
            "resultados_negativos"
        ] = [
            {
                "valor": (
                    formatar_entidade(
                        valor,
                        mapa_rotulos
                    )
                ),
                "id": valor,
                "lucro": round(
                    float(total),
                    2
                )
            }
            for valor, total
            in negativos.items()
        ]

    return resultado


def analisar_dimensoes(
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

    resultado = {}

    for nome_dimensao, config in (
        CONFIG_DIMENSOES.items()
    ):

        # ====================================
        # ENTIDADE COM ID + NOME
        # ====================================

        if "id" in config:

            coluna_id = (
                encontrar_coluna_por_papel(
                    mapeamento,
                    config["id"]
                )
            )

            coluna_rotulo = (
                encontrar_coluna_por_papel(
                    mapeamento,
                    config["rotulo"]
                )
            )

            (
                coluna_agrupamento,
                mapa_rotulos
            ) = preparar_entidade(
                df,
                coluna_id,
                coluna_rotulo
            )

        # ====================================
        # DIMENSÃO NORMAL
        # ====================================

        else:

            coluna_agrupamento = (
                encontrar_coluna_por_papel(
                    mapeamento,
                    config["papel"]
                )
            )

            mapa_rotulos = {}

        if not coluna_agrupamento:
            continue

        resultado[
            nome_dimensao
        ] = analisar_dimensao(
            df,
            nome_dimensao,
            coluna_agrupamento,
            mapa_rotulos,
            coluna_faturamento,
            coluna_lucro,
            coluna_quantidade
        )

    return resultado