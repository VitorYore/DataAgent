import pandas as pd


def gerar_problemas(df: pd.DataFrame, diagnostico: dict) -> list:
    problemas = []

    duplicadas = diagnostico["linhas_duplicadas"]

    if duplicadas > 0:
        problemas.append({
            "tipo": "duplicidade",
            "severidade": "media",
            "mensagem": f"{duplicadas} linhas duplicadas encontradas."
        })

    for coluna, quantidade in diagnostico["valores_nulos"].items():
        if quantidade > 0:
            percentual = diagnostico["percentual_nulos"][coluna]

            problemas.append({
                "tipo": "valor_nulo",
                "coluna": coluna,
                "severidade": "baixa",
                "mensagem": (
                    f"A coluna '{coluna}' possui "
                    f"{quantidade} valores nulos "
                    f"({percentual}%)."
                )
            })

    inferencia = diagnostico["inferencia_tipos"]

    for coluna, dados in inferencia["possiveis_datas"].items():
        problemas.append({
            "tipo": "tipo_incorreto",
            "coluna": coluna,
            "severidade": "media",
            "mensagem": (
                f"A coluna '{coluna}' está como "
                f"{dados['tipo_atual']}, mas parece ser "
                f"datetime com confiança de "
                f"{dados['confianca']}%."
            )
        })

    for coluna, dados in inferencia["possiveis_numeros"].items():
        problemas.append({
            "tipo": "tipo_incorreto",
            "coluna": coluna,
            "severidade": "media",
            "mensagem": (
                f"A coluna '{coluna}' está como "
                f"{dados['tipo_atual']}, mas parece ser "
                f"numérica com confiança de "
                f"{dados['confianca']}%."
            )
        })

    return problemas