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


# The percentage is not informative when the initial value is less than
# this fraction of the series median magnitude.
LIMIAR_BASE_RELATIVA_EVOLUCAO = 0.05


def avaliar_evolucao_total(serie: pd.Series) -> dict:
    """Compare first and last periods while retaining their absolute difference."""
    valores = pd.to_numeric(serie, errors="coerce").dropna()
    if len(valores) < 2:
        return {"variacao_percentual": None, "motivo": "dados_insuficientes", "variacao_absoluta": None}

    inicial = float(valores.iloc[0])
    final = float(valores.iloc[-1])
    absoluta = round(final - inicial, 2)
    resultado = {"variacao_percentual": None, "motivo": None, "variacao_absoluta": absoluta}

    if inicial == 0:
        resultado["motivo"] = "base_zero"
        return resultado
    if inicial * final < 0:
        resultado["motivo"] = "mudanca_de_sinal"
        return resultado

    magnitudes = valores[valores.abs() > 0].abs()
    mediana = float(magnitudes.median()) if not magnitudes.empty else 0.0
    if mediana and abs(inicial) < mediana * LIMIAR_BASE_RELATIVA_EVOLUCAO:
        resultado["motivo"] = "base_muito_baixa"
        return resultado

    resultado["variacao_percentual"] = round((final - inicial) / abs(inicial) * 100, 2)
    return resultado


def calcular_evolucao_total(
    serie: pd.Series
) -> float | None:

    return avaliar_evolucao_total(serie)["variacao_percentual"]


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

    avaliacao_evolucao = avaliar_evolucao_total(faturamento_mensal)
    evolucao_faturamento = avaliacao_evolucao["variacao_percentual"]

    # ========================================
    # 7. RESULTADO BASE
    # ========================================

    resultado = {
        "faturamento": {
            "evolucao_total": evolucao_faturamento,
            "evolucao_motivo": avaliacao_evolucao["motivo"],
            "variacao_absoluta": avaliacao_evolucao["variacao_absoluta"],
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