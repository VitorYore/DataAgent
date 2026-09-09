import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


def converter_para_json(obj):
    if isinstance(obj, np.integer):
        return int(obj)

    if isinstance(obj, np.floating):
        return float(obj)

    if isinstance(obj, np.bool_):
        return bool(obj)

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()

    if isinstance(obj, pd.Period):
        return str(obj)

    raise TypeError(
        f"Objeto do tipo {type(obj).__name__} "
        "não é serializável em JSON"
    )


def salvar_relatorio(
    diagnostico,
    problemas,
    caminho_saida
):
    relatorio = {
        "diagnostico": diagnostico,
        "problemas": problemas
    }

    caminho_saida = Path(caminho_saida)

    caminho_saida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        caminho_saida,
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