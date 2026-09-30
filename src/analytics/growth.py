import pandas as pd

from src.analytics.temporal_comparison import (
    LIMIAR_BASE_RELATIVA, comparar_valores, comparar_serie, magnitude_referencia,
)


LIMIAR_BASE_RELATIVA_EVOLUCAO = LIMIAR_BASE_RELATIVA
MOTIVOS_LEGADOS = {
    "zero_reference": "base_zero", "negative_reference": "base_negativa",
    "sign_change": "mudanca_de_sinal", "low_reference_base": "base_muito_baixa",
    "invalid_value": "dados_insuficientes", "invalid_period": "periodo_invalido",
}


def calcular_variacao(valor_atual: float, valor_anterior: float) -> float | None:
    return comparar_valores(valor_anterior, valor_atual)["percentage_change"]


def avaliar_evolucao_total(serie: pd.Series) -> dict:
    if len(serie) < 2:
        return {"variacao_percentual": None, "motivo": "dados_insuficientes", "variacao_absoluta": None}
    # Não remover valores ausentes: isso mudaria silenciosamente a janela comparada.
    values = serie.sort_index() if not isinstance(serie.index, pd.RangeIndex) else serie
    period_index = isinstance(values.index, pd.PeriodIndex)
    dated = period_index or all(isinstance(p, str) for p in values.index)
    granularity = values.index.freqstr[0] if period_index else "M"
    comparison = comparar_valores(
        values.iloc[0], values.iloc[-1], reference_magnitude=magnitude_referencia(values),
        previous_period=str(values.index[0]) if dated else None,
        current_period=str(values.index[-1]) if dated else None, granularity=granularity,
    )
    return {
        "variacao_percentual": comparison["percentage_change"],
        "variacao_absoluta": round(comparison["absolute_change"], 2) if comparison["absolute_change"] is not None else None,
        "motivo": MOTIVOS_LEGADOS.get(comparison["reason"], comparison["reason"]),
        "comparacao": comparison,
    }


def calcular_evolucao_total(serie: pd.Series) -> float | None:
    return avaliar_evolucao_total(serie)["variacao_percentual"]


def encontrar_sequencias_queda(variacoes: dict) -> list:
    sequencias, atual = [], []
    for periodo, variacao in variacoes.items():
        if variacao is not None and variacao < 0:
            atual.append({"periodo": periodo, "variacao": variacao})
        else:
            if len(atual) >= 2:
                sequencias.append(atual)
            atual = []
    if len(atual) >= 2:
        sequencias.append(atual)
    return sequencias


def definir_tendencia(evolucao: float | None) -> str:
    if evolucao is None:
        return "dados_insuficientes"
    if evolucao > 5:
        return "crescimento"
    if evolucao < -5:
        return "queda"
    return "estavel"


def resumir_crescimento(valores, comparacoes=None):
    comparacoes = comparar_serie(valores) if comparacoes is None else comparacoes
    variacoes = {item["current_period"]: item["percentage_change"] for item in comparacoes}
    serie = pd.Series(valores, dtype=float)
    evolution = avaliar_evolucao_total(serie)
    result = {
        "evolucao_total": evolution["variacao_percentual"], "evolucao_motivo": evolution["motivo"],
        "variacao_absoluta": evolution["variacao_absoluta"],
        "comparacao_total": evolution.get("comparacao"),
        "tendencia": definir_tendencia(evolution["variacao_percentual"]),
        "variacoes": variacoes, "comparacoes": comparacoes,
        "sequencias_queda": encontrar_sequencias_queda(variacoes),
    }
    for key, direction in (("maior_crescimento", 1), ("maior_queda", -1)):
        valid = {p: v for p, v in variacoes.items() if v is not None and v * direction > 0}
        if valid:
            period = max(valid, key=lambda p: valid[p] * direction)
            result[key] = {"periodo": period, "variacao": valid[period]}
    return result


def analisar_crescimento(df: pd.DataFrame, analise_mensal=None, desempenho=None) -> dict:
    # O pipeline fornece séries prontas; chamadas antigas continuam funcionando.
    if analise_mensal is None:
        from src.analytics.temporal import analisar_meses
        analise_mensal = analisar_meses(df)
    if analise_mensal.get("metrica") != "faturamento":
        return {"erro": "Não foi possível identificar Data e uma coluna de faturamento."}
    result = {"faturamento": resumir_crescimento(
        analise_mensal.get("valores_mensais_precisos", analise_mensal.get("valores_mensais", {})),
        analise_mensal.get("comparacoes"))}
    if desempenho is None:
        from src.analytics.performance import analisar_desempenho
        desempenho = analisar_desempenho(df)
    if desempenho.get("lucro_mensal"):
        result["lucro"] = resumir_crescimento(desempenho.get("lucro_mensal_preciso", desempenho["lucro_mensal"]))
    return result
