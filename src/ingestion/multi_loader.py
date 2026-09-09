from pathlib import Path

import pandas as pd
from src.ingestion.loader import carregar_dados


PASTA_DADOS = Path(
    "data/samples"
)

EXTENSOES_SUPORTADAS = [
    ".csv",
    ".xlsx",
    ".xls"
]


def encontrar_arquivos(
    pasta: Path = PASTA_DADOS
) -> list[Path]:

    """
    Procura todos os arquivos de dados
    suportados dentro da pasta.
    """

    if not pasta.exists():

        raise FileNotFoundError(
            f"Pasta não encontrada: {pasta}"
        )

    arquivos = []

    for arquivo in pasta.iterdir():

        if (
            arquivo.is_file()
            and arquivo.suffix.lower()
            in EXTENSOES_SUPORTADAS
        ):

            arquivos.append(
                arquivo
            )

    arquivos.sort(
        key=lambda arquivo: arquivo.name
    )

    if not arquivos:

        raise FileNotFoundError(
            "Nenhuma planilha foi encontrada "
            "em data/samples."
        )

    return arquivos


def carregar_csv(caminho: Path) -> pd.DataFrame:
    return carregar_dados(caminho)


def carregar_arquivo(caminho: Path) -> pd.DataFrame:
    return carregar_dados(caminho)


def criar_nome_tabela(
    caminho: Path
) -> str:

    """
    Usa o nome do arquivo sem a extensão
    como nome da tabela.

    Exemplo:

    Vendas.csv
        ↓
    Vendas
    """

    return caminho.stem


def carregar_multiplas_tabelas(
    pasta: Path = PASTA_DADOS,
    estrito: bool = False
) -> dict[str, pd.DataFrame]:

    """
    Carrega todas as planilhas encontradas
    e retorna um dicionário.

    Exemplo:

    {
        "Vendas": dataframe,
        "Produtos": dataframe,
        "Clientes": dataframe
    }
    """

    arquivos = encontrar_arquivos(
        pasta
    )

    tabelas = {}

    for caminho in arquivos:

        nome_tabela = criar_nome_tabela(
            caminho
        )

        try:

            df = carregar_arquivo(
                caminho
            )

            if estrito and df.empty:
                raise ValueError("A tabela não contém linhas de dados.")

            tabelas[
                nome_tabela
            ] = df

        except Exception as erro:

            if estrito:
                raise ValueError(f"Não foi possível ler a tabela {caminho.name}.") from erro

            print(
                f"\nNão foi possível carregar "
                f"{caminho.name}: {erro}"
            )

    if not tabelas:

        raise ValueError(
            "Nenhuma tabela pôde "
            "ser carregada."
        )

    return tabelas


def gerar_resumo_tabelas(
    tabelas: dict[str, pd.DataFrame]
) -> dict:

    """
    Gera um resumo simples das tabelas
    carregadas.
    """

    resumo = {}

    for nome, df in tabelas.items():

        resumo[
            nome
        ] = {
            "linhas": len(df),
            "colunas": len(
                df.columns
            ),
            "nomes_colunas": list(
                df.columns
            )
        }

    return resumo
