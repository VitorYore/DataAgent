import json
from pathlib import Path

import numpy as np
import pandas as pd


def converter_para_json(obj):
    """
    Converte tipos do Pandas e NumPy
    para tipos que o JSON consegue salvar.
    """

    # ========================================
    # INTEIROS NUMPY
    # ========================================

    if isinstance(
        obj,
        np.integer
    ):
        return int(obj)

    # ========================================
    # FLOATS NUMPY
    # ========================================

    if isinstance(
        obj,
        np.floating
    ):
        return float(obj)

    # ========================================
    # BOOLEANOS NUMPY
    # ========================================

    if isinstance(
        obj,
        np.bool_
    ):
        return bool(obj)

    # ========================================
    # DATAS DO PANDAS
    # ========================================

    if isinstance(
        obj,
        pd.Timestamp
    ):
        return obj.isoformat()

    # ========================================
    # PERÍODOS DO PANDAS
    # ========================================

    if isinstance(
        obj,
        pd.Period
    ):
        return str(obj)

    # ========================================
    # OUTROS TIPOS
    # ========================================

    return str(obj)


def salvar_analise(
    kpis: dict,
    analise_mensal: dict,
    analise_clientes: dict,
    desempenho: dict,
    crescimento: dict,
    dimensoes: dict,
    produtos: dict,
    oportunidades: list,
    insights: list,
    caminho_saida: str = "reports/analise.json"
) -> None:

    caminho = Path(
        caminho_saida
    )

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    relatorio = {
        "kpis": kpis,
        "analise_temporal": analise_mensal,
        "clientes": analise_clientes,
        "desempenho": desempenho,
        "crescimento": crescimento,
        "dimensoes": dimensoes,
        "produtos": produtos,
        "oportunidades": oportunidades,
        "insights": insights
    }

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            relatorio,
            arquivo,
            ensure_ascii=False,
            indent=4,
            default=converter_para_json
        )