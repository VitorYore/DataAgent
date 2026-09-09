import pandas as pd

from src.analytics.column_mapper import mapear_colunas
from src.analytics.business import encontrar_coluna_por_papel


def calcular_variacao(
    valor_atual: float,
    valor_anterior: float
) -> float | None:

    if valor_anterior == 0:
        return None

    variacao = (
        (valor_atual - valor_anterior)
        / abs(valor_anterior)
        * 100
    )

    return round(
        variacao,
        2
    )


def calcular_evolucao_total(
    serie: pd.Series
) -> float | None:

    if len(serie) < 2:
        return None

    primeiro_valor = serie.iloc[0]
    ultimo_valor = serie.iloc[-1]

    return calcular_variacao(
        ultimo_valor,
        primeiro_valor
    )


def encontrar_sequencias_queda(
    variacoes: dict
) -> list:

    sequencias = []
    sequencia_atual = []

    for periodo, variacao in variacoes.items():

        if (
            variacao is not None
            and variacao < 0
        ):

            sequencia_atual.append(
                {
                    "periodo": periodo,
                    "variacao": variacao
                }
            )

        else:

            if len(sequencia_atual) >= 2:

                sequencias.append(
                    sequencia_atual
                )

            sequencia_atual = []

    if len(sequencia_atual) >= 2:

        sequencias.append(
            sequencia_atual
        )

    return sequencias


def definir_tendencia(
    evolucao: float | None
) -> str:

    if evolucao is None:
        return "dados_insuficientes"

    if evolucao > 5:
        return "crescimento"

    if evolucao < -5:
        return "queda"

    return "estavel"


def analisar_crescimento(
    df: pd.DataFrame
) -> dict:

    mapeamento = mapear_colunas(
        df
    )

    coluna_data = encontrar_coluna_por_papel(
        mapeamento,
        "data"
    )

    coluna_faturamento = (
        encontrar_coluna_por_papel(
            mapeamento,
            "faturamento"
        )
    )

    coluna_lucro = encontrar_coluna_por_papel(
        mapeamento,
        "lucro"
    )

    # ========================================
    # 1. VALIDAR COLUNAS
    # ========================================

    if not coluna_data:

        return {
            "erro": (
                "Não foi possível identificar "
                "uma coluna de data."
            )
        }

    if not coluna_faturamento:

        return {
            "erro": (
                "Não foi possível identificar "
                "uma coluna de faturamento."
            )
        }

    # ========================================
    # 2. PREPARAR DADOS
    # ========================================

    colunas_necessarias = [
        coluna_data,
        coluna_faturamento
    ]

    if coluna_lucro:

        colunas_necessarias.append(
            coluna_lucro
        )

    dados = df[
        colunas_necessarias
    ].copy()

    dados = dados.dropna(
        subset=[
            coluna_data,
            coluna_faturamento
        ]
    )

    if dados.empty:

        return {
            "erro": (
                "Não existem dados suficientes "
                "para analisar crescimento."
            )
        }

    # ========================================
    # 3. CRIAR PERÍODO MENSAL
    # ========================================

    dados["Periodo"] = (
        dados[coluna_data]
        .dt.to_period("M")
    )

    # ========================================
    # 4. FATURAMENTO MENSAL
    # ========================================

    faturamento_mensal = (
        dados
        .groupby("Periodo")[
            coluna_faturamento
        ]
        .sum()
        .sort_index()
    )

    # ========================================
    # 5. VARIAÇÃO DO FATURAMENTO
    # ========================================

    variacao_faturamento = {}

    for indice in range(
        1,
        len(faturamento_mensal)
    ):

        periodo_atual = (
            faturamento_mensal.index[
                indice
            ]
        )

        valor_atual = (
            faturamento_mensal.iloc[
                indice
            ]
        )

        valor_anterior = (
            faturamento_mensal.iloc[
                indice - 1
            ]
        )

        variacao = calcular_variacao(
            valor_atual,
            valor_anterior
        )

        variacao_faturamento[
            str(periodo_atual)
        ] = variacao

    # ========================================
    # 6. EVOLUÇÃO GERAL DO FATURAMENTO
    # ========================================

    evolucao_faturamento = (
        calcular_evolucao_total(
            faturamento_mensal
        )
    )

    # ========================================
    # 7. RESULTADO BASE
    # ========================================

    resultado = {
        "faturamento": {
            "evolucao_total": (
                evolucao_faturamento
            ),
            "tendencia": definir_tendencia(
                evolucao_faturamento
            ),
            "variacoes": (
                variacao_faturamento
            ),
            "sequencias_queda": (
                encontrar_sequencias_queda(
                    variacao_faturamento
                )
            )
        }
    }

    # ========================================
    # 8. MAIOR CRESCIMENTO E MAIOR QUEDA
    # ========================================

    variacoes_validas = {
        periodo: valor
        for periodo, valor
        in variacao_faturamento.items()
        if valor is not None
    }

    if variacoes_validas:

        periodo_crescimento = max(
            variacoes_validas,
            key=variacoes_validas.get
        )

        periodo_queda = min(
            variacoes_validas,
            key=variacoes_validas.get
        )

        resultado[
            "faturamento"
        ][
            "maior_crescimento"
        ] = {
            "periodo": periodo_crescimento,
            "variacao": variacoes_validas[
                periodo_crescimento
            ]
        }

        resultado[
            "faturamento"
        ][
            "maior_queda"
        ] = {
            "periodo": periodo_queda,
            "variacao": variacoes_validas[
                periodo_queda
            ]
        }

    # ========================================
    # 9. ANÁLISE DE LUCRO
    # ========================================

    if coluna_lucro:

        lucro_mensal = (
            dados
            .groupby("Periodo")[
                coluna_lucro
            ]
            .sum()
            .sort_index()
        )

        variacao_lucro = {}

        for indice in range(
            1,
            len(lucro_mensal)
        ):

            periodo_atual = (
                lucro_mensal.index[
                    indice
                ]
            )

            valor_atual = (
                lucro_mensal.iloc[
                    indice
                ]
            )

            valor_anterior = (
                lucro_mensal.iloc[
                    indice - 1
                ]
            )

            variacao = calcular_variacao(
                valor_atual,
                valor_anterior
            )

            variacao_lucro[
                str(periodo_atual)
            ] = variacao

        evolucao_lucro = (
            calcular_evolucao_total(
                lucro_mensal
            )
        )

        resultado["lucro"] = {
            "evolucao_total": (
                evolucao_lucro
            ),
            "tendencia": definir_tendencia(
                evolucao_lucro
            ),
            "variacoes": variacao_lucro,
            "sequencias_queda": (
                encontrar_sequencias_queda(
                    variacao_lucro
                )
            )
        }

        variacoes_lucro_validas = {
            periodo: valor
            for periodo, valor
            in variacao_lucro.items()
            if valor is not None
        }

        if variacoes_lucro_validas:

            periodo_crescimento = max(
                variacoes_lucro_validas,
                key=variacoes_lucro_validas.get
            )

            periodo_queda = min(
                variacoes_lucro_validas,
                key=variacoes_lucro_validas.get
            )

            resultado[
                "lucro"
            ][
                "maior_crescimento"
            ] = {
                "periodo": periodo_crescimento,
                "variacao": (
                    variacoes_lucro_validas[
                        periodo_crescimento
                    ]
                )
            }

            resultado[
                "lucro"
            ][
                "maior_queda"
            ] = {
                "periodo": periodo_queda,
                "variacao": (
                    variacoes_lucro_validas[
                        periodo_queda
                    ]
                )
            }

    return resultado