"""Heurísticas conservadoras de estrutura; não corrige valores de negócio."""
import re
import unicodedata

import pandas as pd


TERMOS = set('data cliente produto valor total custo lucro pedido id quantidade preco status forma pagamento nome codigo descricao venda receita faturamento estoque canal loja'.split())


def vazio(valor):
    return pd.isna(valor) or (isinstance(valor, str) and not valor.strip())


def _texto(valor):
    if vazio(valor) or not isinstance(valor, str):
        return False
    texto = valor.strip()
    if texto.lower().startswith('unnamed:'):
        return False
    # Arquivos já exportados pelo DataAgent também possuem cabeçalhos genéricos.
    if re.fullmatch(r'coluna_\d+(?:_\d+)?', texto):
        return True
    # Datas, moedas e códigos com dígitos são evidência de dados, não labels.
    return not re.search(r'\d', texto)


def detectar_cabecalho(amostra):
    """Retorna índice base zero e confiança heurística (não probabilidade)."""
    if amostra.empty:
        return None, 0.0
    ativos = [i for i in range(amostra.shape[1]) if any(not vazio(v) for v in amostra.iloc[:, i])]
    melhor, confianca = None, 0.0
    for indice in range(min(20, len(amostra))):
        valores = [amostra.iloc[indice, i] for i in ativos]
        preenchidos = [v for v in valores if not vazio(v)]
        if not preenchidos:
            continue
        cobertura = len(preenchidos) / max(1, len(ativos))
        textos = sum(_texto(v) for v in preenchidos) / len(preenchidos)
        distintos = len({str(v).strip() for v in preenchidos}) / len(preenchidos)
        termos = 0
        for valor in preenchidos:
            nome = ''.join(c for c in unicodedata.normalize('NFKD', str(valor).lower()) if not unicodedata.combining(c))
            termos += bool(set(re.findall(r'[a-z]+', nome)) & TERMOS)
        seguintes = amostra.iloc[indice + 1:indice + 6]
        mudancas = []
        for i in ativos:
            posteriores = [v for v in seguintes.iloc[:, i] if not vazio(v)]
            if posteriores and _texto(amostra.iloc[indice, i]):
                mudancas.append(sum(not _texto(v) for v in posteriores) / len(posteriores))
        contraste = sum(mudancas) / max(1, len(ativos))
        # Apenas texto não basta: exige vocabulário de coluna ou contraste de tipos.
        # A exceção de arquivo contendo apenas labels não se aplica à última
        # linha de dados ou ao fim da amostra de 20 linhas.
        somente_labels = len(amostra) == 1 and textos == 1 and distintos == 1 and cobertura == 1 and len(preenchidos) >= 2
        if textos < 0.5 or cobertura < 0.5 or not (termos >= 2 or contraste >= 0.25 or (termos and textos >= 0.75) or somente_labels):
            continue
        score = 0.4 * textos + 0.15 * cobertura + 0.1 * distintos + 0.15 * min(1, termos / 2) + 0.2 * contraste
        if somente_labels:
            score = max(score, 0.75)
        if score >= 0.7 and score > confianca:
            melhor, confianca = indice, score
    return melhor, round(confianca * 100, 2)


def preparar_tabela(df, nomes, diagnostico):
    """Remove somente eixos totalmente vazios e normaliza exclusivamente nomes."""
    mascara = df.apply(lambda coluna: coluna.map(vazio))
    linhas_vazias = mascara.all(axis=1)
    colunas_vazias = mascara.all(axis=0)
    diagnostico['linhas_vazias_removidas'] += int(linhas_vazias.sum())
    diagnostico['colunas_vazias_removidas'] = int(colunas_vazias.sum())
    indices = [i for i, remover in enumerate(colunas_vazias) if not remover]
    df = df.loc[~linhas_vazias].iloc[:, indices].copy()
    usados, novos, alteracoes = set(), [], []
    originais = [nomes[i] if i < len(nomes) else None for i in indices]
    reservados = {str(v).strip() for v in originais if not vazio(v)}
    for i, original in zip(indices, originais):
        antigo = '' if vazio(original) else str(original)
        base = antigo.strip()
        if not base or base.lower().startswith('unnamed:'):
            base = f'coluna_{i + 1}'
        novo, sufixo = base, 2
        while novo in usados or (novo in reservados and novo != antigo.strip()):
            novo = f'{base}_{sufixo}'
            sufixo += 1
        usados.add(novo)
        novos.append(novo)
        if antigo != novo:
            alteracoes.append({'posicao': i + 1, 'original': antigo, 'novo': novo})
    df.columns = novos
    diagnostico['colunas_renomeadas'] = alteracoes  # Lista preserva nomes originais repetidos.
    diagnostico['colunas_suspeitas'] = [nome for nome in novos if not _texto(nome)]
    diagnostico['colunas_muitos_nulos'] = {
        nome: round(float(mascara.iloc[:, i].mean() * 100), 2)
        for i, nome in zip(indices, novos) if mascara.iloc[:, i].mean() >= 0.95
    }
    df.attrs['ingestao'] = diagnostico
    return df.reset_index(drop=True)
