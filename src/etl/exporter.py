from pathlib import Path

import pandas as pd


def salvar_dados_tratados(
    df: pd.DataFrame,
    caminho_saida: str = "data/processed/vendas_tratadas.csv"
) -> None:

    caminho = Path(caminho_saida)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        caminho,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )