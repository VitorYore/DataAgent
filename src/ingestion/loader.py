from pathlib import Path
import csv
from collections import Counter

import pandas as pd
from src.ingestion.structure_inspector import detectar_cabecalho, preparar_tabela, vazio


PASTA_DADOS = Path("data/samples")


def encontrar_arquivo() -> Path:

    extensoes_permitidas = [
        "*.csv",
        "*.xlsx",
        "*.xls"
    ]

    arquivos = []

    for extensao in extensoes_permitidas:
        arquivos.extend(
            PASTA_DADOS.glob(extensao)
        )

    if not arquivos:
        raise FileNotFoundError(
            "Nenhuma planilha foi encontrada "
            "em data/samples."
        )

    if len(arquivos) > 1:
        raise ValueError(
            "Mais de uma planilha foi encontrada "
            "em data/samples. Deixe apenas o arquivo "
            "que deseja analisar."
        )

    return arquivos[0]


def carregar_dados(
    caminho=None
) -> pd.DataFrame:

    if caminho is None:
        caminho = encontrar_arquivo()

    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}"
        )

    extensao = caminho.suffix.lower()

    if extensao == '.csv':
        for encoding in ('utf-8-sig', 'latin1'):
            try:
                return _carregar_csv(caminho, encoding)
            except UnicodeDecodeError:
                if encoding == 'latin1':
                    raise
    elif extensao in ('.xlsx', '.xls'):
        amostra = pd.read_excel(caminho, header=None, nrows=20)
        indice, confianca = detectar_cabecalho(amostra)
        nomes = list(amostra.iloc[indice]) if indice is not None else []
        df = pd.read_excel(caminho, header=None, skiprows=indice + 1 if indice is not None else 0)
        # Mantém posições inclusive de colunas vazias explicitamente nomeadas.
        df = df.reindex(columns=range(max(df.shape[1], len(nomes))))
        return preparar_tabela(df, nomes, _diagnostico(caminho, amostra, indice, confianca))
    else:

        raise ValueError(
            f"Formato de arquivo não suportado: "
            f"{extensao}"
        )


def _diagnostico(caminho, amostra, indice, confianca):
    return {
        'arquivo': caminho.name,
        'cabecalho_detectado': indice is not None,
        'linha_cabecalho': indice + 1 if indice is not None else None,
        'confianca_cabecalho': confianca,
        'linhas_anteriores_cabecalho': indice or 0,
        'linhas_vazias_removidas': sum(
            all(vazio(v) for v in linha)
            for linha in amostra.iloc[:indice or 0].itertuples(index=False, name=None)
        ),
    }


def _carregar_csv(caminho, encoding):
    with caminho.open(encoding=encoding, newline='') as arquivo:
        trecho = arquivo.read(65536)
    # Escolhe somente separadores comuns, pela regularidade de linhas multicoluna.
    scores = {}
    for separador in (',', ';', '\t', '|'):
        leitor = csv.reader(trecho.splitlines(), delimiter=separador)
        contagens = Counter(len(linha) for _, linha in zip(range(20), leitor) if len(linha) > 1)
        scores[separador] = max(((frequencia, largura) for largura, frequencia in contagens.items()), default=(0, 0))
    separador = max(scores, key=scores.get)
    registros, finais = [], []
    with caminho.open(encoding=encoding, newline='') as arquivo:
        leitor = csv.reader(arquivo, delimiter=separador, strict=True)
        for _, linha in zip(range(20), leitor):
            registros.append(linha)
            finais.append(leitor.line_num)
    if not registros:
        raise pd.errors.EmptyDataError('O arquivo CSV está vazio.')
    amostra = pd.DataFrame(registros)
    indice, confianca = detectar_cabecalho(amostra)
    nomes = registros[indice] if indice is not None else []
    skip = finais[indice] if indice is not None else 0
    df = pd.read_csv(caminho, encoding=encoding, sep=separador, header=None,
                     names=range(amostra.shape[1]), skiprows=skip, skip_blank_lines=False)
    diagnostico = _diagnostico(caminho, amostra, indice, confianca)
    diagnostico.update(encoding=encoding, separador=separador)
    if indice is not None:
        diagnostico['linha_cabecalho'] = (finais[indice - 1] if indice else 0) + 1
    return preparar_tabela(df, nomes, diagnostico)
