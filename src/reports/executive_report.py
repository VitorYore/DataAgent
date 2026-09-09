import json
from pathlib import Path


CAMINHO_RELATORIO = Path(
    "reports/resumo_executivo.json"
)


def salvar_resumo_executivo(
    resumo: dict,
    caminho: Path = CAMINHO_RELATORIO
):

    """
    Salva o resumo executivo em JSON.

    Esse arquivo é pensado principalmente
    para consumo pelo frontend/API.
    """

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            resumo,
            arquivo,
            ensure_ascii=False,
            indent=4,
            default=str
        )

    return str(
        caminho
    )