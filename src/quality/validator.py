import pandas as pd
from src.quality.type_inference import inferir_tipos

def indentificar_colunas(df: pd.DataFrame) -> dict:
    colunas_numericas = df.select_dtypes(
        include = "number"
    ).columns.tolist()

    colunas_texto = df.select_dtypes(
        include=["object", "string"]
    ).columns.tolist()

    colunas_data = df.select_dtypes(
        include=["datetime","datetimetz"]
    ).columns.tolist()

    return{
        "numericas": colunas_numericas,
        "texto": colunas_texto,
        "data": colunas_data
    }

def gerar_diagnostico(df: pd.DataFrame) -> dict:
    diagnostico = {
        "quantidade_linhas": len(df),

        "quantidade_colunas": len(df.columns),

        "colunas": list(df.columns),

        "tipos_dados":{
            coluna: str(tipo)
            for coluna, tipo in df.dtypes.items()
        },

        "tipos_colunas": indentificar_colunas(df),

        "inferencia_tipos": inferir_tipos(df),

        "valores_nulos": df.isnull().sum().to_dict(),

        "percentual_nulos": (
            df.isnull().mean() *100
        ).round(2).to_dict(),

        "linhas_duplicadas": int(
            df.duplicated().sum()
        ),
    }

    if 'ingestao' in df.attrs:
        diagnostico['ingestao'] = df.attrs['ingestao']
    return diagnostico
