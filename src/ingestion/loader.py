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


def _carregar_convencional(
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
    separador = _separador_csv(caminho, encoding)
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


def _separador_csv(caminho, encoding):
    with caminho.open(encoding=encoding, newline='') as arquivo:
        trecho = arquivo.read(65536)
    # Escolhe somente separadores comuns, pela regularidade de linhas multicoluna.
    scores = {}
    for separador in (',', ';', '\t', '|'):
        leitor = csv.reader(trecho.splitlines(), delimiter=separador)
        contagens = Counter(len(linha) for _, linha in zip(range(20), leitor) if len(linha) > 1)
        scores[separador] = max(((frequencia, largura) for largura, frequencia in contagens.items()), default=(0, 0))
    return max(scores, key=scores.get)


def carregar_tabelas_arquivo(caminho):
    """Inspeciona cada aba sem combinar estruturas incompatíveis."""
    from src.ingestion.report_normalizer import normalizar_relatorio, StructuralReviewRequired
    caminho = Path(caminho)
    evidencias = {}
    if caminho.suffix.lower() == '.csv':
        for encoding in ('utf-8-sig', 'latin1'):
            try:
                sep = _separador_csv(caminho, encoding)
                with caminho.open(encoding=encoding, newline='') as stream:
                    rows = list(csv.reader(stream, delimiter=sep, strict=True))
                break
            except UnicodeDecodeError:
                if encoding == 'latin1':
                    raise
        abas = {'CSV': pd.DataFrame(rows)}
    elif caminho.suffix.lower() in ('.xlsx', '.xls'):
        abas = pd.read_excel(caminho, sheet_name=None, header=None)
        if caminho.suffix.lower() == '.xlsx':
            from openpyxl import load_workbook
            book = load_workbook(caminho, data_only=False)
            try:
                for sheet in book:
                    formulas = []
                    raw = abas[sheet.title]
                    for row in sheet:
                        for cell in row:
                            if cell.data_type == 'f':
                                cached = raw.iloc[cell.row - 1, cell.column - 1] if cell.row <= len(raw) and cell.column <= raw.shape[1] else None
                                formulas.append({'linha': cell.row, 'coluna': cell.column, 'formula': cell.value, 'sem_cache': bool(vazio(cached))})
                                # Fórmula sem cache não pode desaparecer como célula vazia.
                                if vazio(cached):
                                    if cell.row > len(raw) or cell.column > raw.shape[1]:
                                        raw = raw.reindex(index=range(max(len(raw), cell.row)), columns=range(max(raw.shape[1], cell.column)))
                                    coluna = raw.columns[cell.column - 1]
                                    if raw[coluna].dtype != object:
                                        raw[coluna] = raw[coluna].astype(object)
                                    raw.iloc[cell.row - 1, cell.column - 1] = cell.value
                    abas[sheet.title] = raw
                    evidencias[sheet.title] = {'formulas': formulas, 'celulas_mescladas': [str(r) for r in sheet.merged_cells.ranges]}
            finally:
                book.close()
    else:
        return {caminho.stem: _carregar_convencional(caminho)}
    tabelas, diagnosticos = {}, {}
    revisao = False
    for aba, bruto in abas.items():
        if bruto.empty or bruto.map(vazio).all().all():
            diagnosticos[aba] = {'estrutura_detectada': 'aba_vazia', 'linhas_originais': len(bruto)}
            continue
        resultado = normalizar_relatorio(bruto, {'arquivo': caminho.name, 'aba': aba}, evidencias.get(aba))
        if resultado['aplicado']:
            diagnosticos[aba] = resultado['metadados']
            if resultado['metadados']['revisao_necessaria']:
                revisao = True
            blocos = resultado['blocos']
        elif len(abas) == 1:
            blocos = [_carregar_convencional(caminho)]
        else:
            indice, confianca = detectar_cabecalho(bruto.head(20))
            nomes = list(bruto.iloc[indice]) if indice is not None else []
            blocos = [preparar_tabela(bruto.iloc[indice + 1 if indice is not None else 0:].infer_objects(), nomes,
                                     _diagnostico(caminho, bruto, indice, confianca))]
        for i, df in enumerate(blocos):
            df.attrs['ingestao'].update(arquivo=caminho.name, aba=aba)
            chave = caminho.stem if len(abas) == 1 and len(blocos) == 1 else f'{caminho.stem}__{aba}__{i + 1}'
            tabelas[chave] = df
    if revisao:
        raise StructuralReviewRequired({'arquivo': caminho.name, 'abas': diagnosticos})
    if not tabelas:
        raise StructuralReviewRequired({'arquivo': caminho.name, 'abas': diagnosticos, 'motivo': 'Nenhum registro identificado.'})
    # Continuação somente com nomes reais idênticos e tipos compatíveis. Tabelas
    # sem cabeçalho permanecem independentes, ainda que tenham a mesma largura.
    grupos = {}
    for nome, df in tabelas.items():
        info = df.attrs['ingestao']
        chave = (tuple(df.columns), tuple(str(t) for t in df.dtypes)) if info.get('cabecalho_detectado') else (nome,)
        grupos.setdefault(chave, []).append((nome, df))
    saida = {}
    for grupo in grupos.values():
        nome, df = grupo[0]
        if len(grupo) > 1:
            infos = {n: d.attrs['ingestao'] for n, d in grupo}
            df = pd.concat([d for _, d in grupo], ignore_index=True)
            df.attrs['ingestao'] = {**grupo[0][1].attrs['ingestao'], 'continuacoes': infos}
        if diagnosticos:
            df.attrs['ingestao']['abas_inspecionadas'] = list(abas)
            if len(abas) > 1:
                df.attrs['ingestao']['diagnosticos_abas'] = diagnosticos
        saida[nome] = df
    return saida


def carregar_dados(caminho=None):
    from src.ingestion.report_normalizer import StructuralReviewRequired
    tabelas = carregar_tabelas_arquivo(caminho or encontrar_arquivo())
    if len(tabelas) != 1:
        raise StructuralReviewRequired({'motivo': 'Múltiplas tabelas independentes; utilizar carregamento multitabela.', 'tabelas': list(tabelas)})
    return next(iter(tabelas.values()))
