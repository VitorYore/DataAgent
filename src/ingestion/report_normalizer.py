"""Normalização determinística, conservadora e auditável de regiões de relatórios.

Confianças são scores heurísticos, não probabilidades. Não infere conceitos de negócio.
"""
from collections import Counter
from datetime import date, datetime
import math
import re
import unicodedata

import pandas as pd

from src.ingestion.structure_inspector import detectar_cabecalho, preparar_tabela, vazio
from src.ingestion.row_patterns import inspecionar_padrao, compatibilidade


class StructuralReviewRequired(ValueError):
    def __init__(self, diagnostico):
        super().__init__('A estrutura da planilha necessita revisão. Consulte o diagnóstico estrutural.')
        self.diagnostico = diagnostico

    def detalhe_publico(self):
        abas = list(self.diagnostico.get('abas', {}).values())
        confiancas = [a['confianca_estrutural'] for a in abas if 'confianca_estrutural' in a]
        def total(campo):
            valores = [a[campo] for a in abas if campo in a]
            return sum(valores) if valores else None
        return {
            'mensagem': 'Estrutura não reconhecida com segurança.',
            'confianca': min(confiancas) if confiancas else None,
            'unidade_confianca': 'percentual',
            'motivo': self.diagnostico.get('motivo') or next((a.get('motivo') for a in abas if a.get('revisao_necessaria') and a.get('motivo')), 'Nenhum bloco transacional atingiu os critérios de extração segura.'),
            'linhas_com_conteudo': total('linhas_com_conteudo'),
            'linhas_transacionais': total('registros_extraidos'),
            'linhas_desconhecidas': total('linhas_desconhecidas'),
            'diagnostico': 'diagnostico_estrutural.json',
        }


MOEDAS = ('R$', 'US$', '$', '£', '€', '¥', '₹')
MESES = 'janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro january february march april may june july august september october november december'.split()
RESUMOS = re.compile(r'^(?:(?:\d+(?:[.,]\d+)?\s+)?dias uteis|subtotal|total|meta|media|saldo|resultado|percentual|average|target|balance)(?:\s|:|$)')
COMENTARIOS = re.compile(r'^(obs\.?|observacao|observacoes|nota|notas|comentario|comentarios|fonte)(?:\s|:|$)')


def texto(v):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(v).strip().lower()) if not unicodedata.combining(c))


def numero(v):
    """Parser local: formatos inequívocos; separador único com três dígitos é ambíguo."""
    if vazio(v) or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    s = str(v).strip()
    negativo = s.startswith('(') and s.endswith(')')
    if negativo:
        s = s[1:-1]
    for moeda in MOEDAS:
        s = s.replace(moeda, '')
    s = s.replace(' ', '').replace('\xa0', '')
    if not re.fullmatch(r'[+-]?\d[\d.,]*', s):
        return None
    if '.' in s and ',' in s:
        decimal = '.' if s.rfind('.') > s.rfind(',') else ','
        milhar = ',' if decimal == '.' else '.'
        inteiro, fracao = s.rsplit(decimal, 1)
        if not re.fullmatch(r'[+-]?\d{1,3}(?:' + re.escape(milhar) + r'\d{3})+', inteiro) or not fracao.isdigit():
            return None
        s = inteiro.replace(milhar, '') + '.' + fracao
    elif ',' in s or '.' in s:
        sep = ',' if ',' in s else '.'
        if s.count(sep) != 1 or len(s.rsplit(sep, 1)[1]) == 3:
            return None
        s = s.replace(sep, '.')
    try:
        resultado = float(s) * (-1 if negativo else 1)
        return resultado if math.isfinite(resultado) else None
    except ValueError:
        return None


def eh_data(v):
    if isinstance(v, (date, datetime, pd.Timestamp)):
        return not pd.isna(v)
    s = str(v).strip()
    for padrao, formato in ((r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'), (r'\d{1,2}/\d{1,2}/\d{4}', '%d/%m/%Y')):
        if re.fullmatch(padrao, s):
            try:
                datetime.strptime(s, formato)
                return True
            except ValueError:
                pass
    return False


def tipo_celula(v):
    if vazio(v):
        return '_'
    if eh_data(v):
        return 'D'
    if str(v).strip() in MOEDAS:
        return '$'
    if isinstance(v, str) and v.strip().endswith('%') and numero(v.strip()[:-1]) is not None:
        return 'P'
    if numero(v) is not None:
        return 'N'
    return 'T'


def seguro(v):
    if vazio(v):
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return str(v)
    return v if isinstance(v, (str, int, float, bool)) else str(v)


def periodo(valores):
    preenchidos = [texto(v) for v in valores if not vazio(v)]
    if len(preenchidos) > 2:
        return None
    s = ' '.join(preenchidos)
    meses = '|'.join(sorted(set(MESES + [m[:3] for m in MESES]), key=len, reverse=True))
    if re.fullmatch(r'(?:' + meses + r')(?:[ /-]+\d{4})?|\d{4}(?:[ /-]+(?:' + meses + r'))?|[1-4][ºo°]?\s*trimestre(?:[ /-]+\d{4})?|q[1-4](?:[ /-]+\d{4})?', s):
        return ' '.join(str(v).strip() for v in valores if not vazio(v))
    return None


def normalizar_relatorio(bruto, origem=None, evidencias=None):
    """Retorna regiões separadas e auditoria; tabela convencional retorna aplicado=False.

    Ambiguidades em relatório complexo impedem o envio parcial para a análise.
    Todas as linhas não transacionais são preservadas com coordenadas e valores.
    """
    evidencias = evidencias or {}
    # Regiões laterais só são independentes quando um corredor vazio separa
    # cabeçalhos em linhas diferentes. Uma coluna vazia numa tabela não basta.
    ativos = [i for i in range(bruto.shape[1]) if not bruto.iloc[:, i].map(vazio).all()]
    regioes = []
    for i in ativos:
        if not regioes or i != regioes[-1][-1] + 1:
            regioes.append([])
        regioes[-1].append(i)
    headers_regioes = [detectar_cabecalho(bruto.iloc[:, cols].head(20))[0] for cols in regioes]
    if len(regioes) > 1 and all(len(c) >= 2 for c in regioes) and all(h is not None for h in headers_regioes) and len(set(headers_regioes)) > 1:
        saidas, metas = [], []
        for cols in regioes:
            parte = bruto.iloc[:, cols].copy()
            parte.columns = range(len(cols))
            sub = normalizar_relatorio(parte, {**(origem or {}), 'colunas_origem': [c + 1 for c in cols]})
            if sub['aplicado']:
                saidas.extend(sub['blocos']); metas.append(sub['metadados'])
            else:
                h, conf = detectar_cabecalho(parte.head(20))
                diag = {'cabecalho_detectado': h is not None, 'linha_cabecalho': h + 1 if h is not None else None, 'confianca_cabecalho': conf, 'linhas_vazias_removidas': 0}
                tabela = preparar_tabela(parte.iloc[h + 1 if h is not None else 0:].infer_objects(), list(parte.iloc[h]) if h is not None else [], diag)
                saidas.append(tabela)
                metas.append({'colunas_origem': [c + 1 for c in cols], 'linha_cabecalho': diag['linha_cabecalho'], 'registros_extraidos': len(tabela)})
        meta = {'estrutura_detectada': 'multiplas_regioes', 'origem': origem, 'linhas_originais': len(bruto), 'quantidade_blocos': len(saidas), 'regioes': metas, 'evidencias_excel': evidencias, 'revisao_necessaria': True,
                'motivo': 'Regiões laterais separadas; revisão necessária antes de selecionar ou relacionar tabelas.'}
        # As regiões ficam disponíveis para inspeção, mas não se escolhe uma
        # região automaticamente nem se perdem células fora das tabelas.
        meta['linhas_preservadas'] = [[seguro(v) for v in row] for row in bruto.itertuples(index=False, name=None)]
        return {'aplicado': True, 'blocos': saidas, 'metadados': meta}
    linhas = list(bruto.itertuples(index=False, name=None))
    assinaturas = [tuple(tipo_celula(v) for v in row) for row in linhas]
    contagens = Counter(s for s in assinaturas if sum(c not in ('_', '$') for c in s) >= 2)
    header, confianca_header = detectar_cabecalho(bruto.head(20))
    formulas_agregadas = {f['linha'] - 1 for f in evidencias.get('formulas', []) if re.search(r'\b(?:SUM|SUBTOTAL|AVERAGE|COUNT|COUNTA|MIN|MAX)\s*\(', str(f.get('formula', '')), re.I)}
    cabecalhos = {}
    tipos = []
    for i, (row, assinatura) in enumerate(zip(linhas, assinaturas)):
        preenchidos = [v for v in row if not vazio(v)]
        label = texto(preenchidos[0]) if preenchidos else ''
        tipo = None
        if not preenchidos:
            tipo = 'vazia'
        elif i in formulas_agregadas and len(preenchidos) <= 3:
            tipo = 'resumo'
        elif periodo(row):
            tipo = 'periodo'
        elif RESUMOS.match(label):
            tipo = 'desconhecida' if 'D' in assinatura else 'meta' if label.startswith(('meta', 'target')) else 'subtotal' if label.startswith('subtotal') else 'total' if label.startswith('total') else 'resumo'
        elif COMENTARIOS.match(label) and len(preenchidos) <= 2:
            tipo = 'comentario'
        elif len(preenchidos) == 1 and re.fullmatch(r'[-_=.* ]+', str(preenchidos[0])):
            tipo = 'separador'
        elif assinatura.count('T') >= 2 and 'D' not in assinatura and 'N' not in assinatura:
            indice, confianca = detectar_cabecalho(bruto.iloc[i:i + 6].reset_index(drop=True))
            if indice == 0 and (i == header or i + 1 < len(linhas)):
                cabecalhos[i] = (list(row), confianca)
                tipo = 'cabecalho'
        tipos.append(tipo)

    conhecidos = {tuple(texto(v) for v in nomes): confianca for nomes, confianca in cabecalhos.values()}
    for i, row in enumerate(linhas):
        chave = tuple(texto(v) for v in row)
        if chave in conhecidos:
            tipos[i] = 'cabecalho'
            cabecalhos[i] = (list(row), conhecidos[chave])
    if cabecalhos:
        header = min(cabecalhos)

    compostos = []
    for i in sorted(cabecalhos):
        if i == 0:
            continue
        pai = list(linhas[i - 1])
        mesclado = False
        for faixa in evidencias.get('celulas_mescladas', []):
            from openpyxl.utils.cell import range_boundaries
            c1, l1, c2, l2 = range_boundaries(faixa)
            if l1 == l2 == i and c2 > c1 and c2 <= len(pai):
                mesclado = True
                for c in range(c1 - 1, c2):
                    pai[c] = pai[c1 - 1]
        if i - 1 not in cabecalhos and not mesclado:
            continue
        filho, conf = cabecalhos[i]
        if sum(not vazio(v) for v in linhas[i - 1]) < 2:
            continue  # Um título não é uma linha de rótulos.
        nomes = [' / '.join(dict.fromkeys(str(v).strip() for v in (p, f) if not vazio(v))) or None for p, f in zip(pai, filho)]
        cabecalhos[i] = (nomes, conf)
        tipos[i - 1] = 'cabecalho_superior'
        compostos.append({'tipo': 'cabecalho_composto', 'linhas': [i, i + 1], 'nomes': nomes})

    # Não altera linhas parciais/esparsas de tabelas convencionais. Não basta estar
    # sem cabeçalho para acionar normalização. Símbolos/fórmulas exigem inspeção.
    complexa = any(t in ('periodo', 'meta', 'subtotal', 'total', 'resumo', 'comentario', 'separador') for t in tipos)
    complexa |= len(cabecalhos) > 1 or bool(evidencias.get('formulas'))
    complexa |= bool(compostos)
    complexa |= header is not None and header >= 20
    complexa |= 'desconhecida' in tipos
    complexa |= any('$' in s for s in assinaturas)
    complexa |= any(isinstance(v, str) and numero(v) is not None and (any(m in v for m in MOEDAS) or (',' in v and '.' in v) or (v.strip().startswith('(') and v.strip().endswith(')'))) for row in linhas for v in row)
    densas = [s for s, n in contagens.items() if n >= 2 and sum(c != '_' for c in s) >= 3]
    complexa |= bool(densas) and any(s.count('T') == 1 and sum(c != '_' for c in s) == 1 for s in assinaturas[header + 1 if header is not None else 0:])
    if not complexa:
        return {'aplicado': False, 'blocos': [], 'metadados': {}}

    repeticao = inspecionar_padrao(linhas, assinaturas, tipos, evidencias.get('formulas', []))
    forte = bool(repeticao.get('forte_global') or repeticao['fortes']) and repeticao['compatibilidade'] >= 95 and not repeticao['incompativeis']
    ancora = repeticao['ids'] + repeticao['datas']
    em_resumo = False
    if forte:
        for i, (row, sig) in enumerate(zip(linhas, assinaturas)):
            perfil = repeticao['ajustadas'][i]
            identidade = any(sig[c] == 'N' for c in repeticao['ids']) or any(sig[c] == 'D' for c in repeticao['datas'])
            formulas_linha = repeticao['formulas_por_linha'][i]
            agregado = any(re.search(r'\b(?:SUM|SUBTOTAL|AVERAGE|COUNT|COUNTA|MIN|MAX)\s*\(', str(f['formula']), re.I) for f in formulas_linha)
            if tipos[i] in ('periodo', 'cabecalho'):
                em_resumo = False
            if not identidade and agregado:
                tipos[i] = 'total'
            elif tipos[i] is None and not identidade and em_resumo and sum(t not in ('_', '$') for t in sig) <= 3 and 'D' not in sig and (any(t in ('N', 'P') for t in sig) or formulas_linha):
                tipos[i] = 'resumo'
            if tipos[i] in ('total', 'subtotal', 'resumo', 'meta'):
                em_resumo = True
            elif tipos[i] is None and compatibilidade(perfil, repeticao['dominante']) >= 0.95:
                em_resumo = False

    auditoria, blocos, contexto, atual = [], [], None, None
    formulas_indisponiveis = []
    formulas = {item['linha'] for item in evidencias.get('formulas', []) if item.get('sem_cache')}
    top = [s for s, count in contagens.most_common(32) if count >= 2]
    for i, (row, sig, tipo) in enumerate(zip(linhas, assinaturas, tipos)):
        dados = sum(c not in ('_', '$') for c in sig)
        similar = max((sum(a == b or a == '_' for a, b in zip(sig, p)) / max(1, len(sig)) for p in top), default=0)
        score = 0.45 * (contagens[sig] >= 2 or similar >= 0.85) + 0.25 * ('D' in sig or 'N' in sig) + 0.2 * (dados >= 2) + 0.1 * (atual is not None)
        if tipo == 'periodo':
            contexto = periodo(row)
        if tipo == 'cabecalho':
            nomes, confiança = cabecalhos[i]
            if atual is None or [texto(v) for v in nomes] != [texto(v) for v in atual['nomes']]:
                atual = {'nomes': nomes, 'linhas': [], 'indices': [], 'cabecalho': i + 1, 'confianca': confiança}
                blocos.append(atual)
        if tipo is None:
            # Títulos antes do cabeçalho são mantidos na auditoria, não viram dados.
            if header is not None and i < header and dados <= 1:
                tipo = 'titulo'
            elif forte and dados < max(3, sum(t not in ('_', '$') for t in repeticao['dominante']) * 0.6):
                tipo = 'desconhecida'
            elif i + 1 in formulas and not (forte and i in repeticao['fortes'] and all(f['coluna'] - 1 in repeticao['opcionais'] for f in repeticao['formulas_por_linha'][i] if f.get('sem_cache'))):
                tipo = 'desconhecida'
            elif (forte and i in repeticao['fortes']) or score >= 0.8 or (atual is not None and dados >= 2 and ('N' in sig or 'D' in sig) and similar >= 0.5):
                tipo = 'transacao'
                if atual is None:
                    atual = {'nomes': [], 'linhas': [], 'indices': [], 'cabecalho': None, 'confianca': 0}
                    blocos.append(atual)
                if atual.get('assinatura') is not None and not (forte and i in repeticao['fortes']):
                    anterior = atual['assinatura']
                    conflitos = sum(a != b and a != '_' and b != '_' for a, b in zip(sig, anterior))
                    if conflitos > max(1, dados // 3):
                        tipo = 'desconhecida'
                atual.setdefault('assinatura', sig)
                if tipo == 'transacao':
                    registro = list(row)
                    for f in repeticao['formulas_por_linha'][i]:
                        if f.get('sem_cache'):
                            registro[f['coluna'] - 1] = None
                            formulas_indisponiveis.append({**f, 'tratamento': 'Valor indisponível preservado como nulo; fórmula não recalculada.'})
                    atual['linhas'].append(registro)
                    atual['indices'].append(i + 1)
            else:
                tipo = 'desconhecida'
        item = {'linha': i + 1, 'tipo': tipo, 'confianca': round(score * 100, 2) if tipo == 'transacao' else 100 if tipo != 'desconhecida' else 0}
        if contexto:
            item['periodo_contexto'] = contexto
        datas = [seguro(v) for v in row if eh_data(v)]
        if datas:
            item['datas_registro'] = datas  # Nunca preenche ou substitui data usando contexto.
        if tipo != 'transacao':
            item['valores'] = [seguro(v) for v in row]
        auditoria.append(item)

    # Continuação comprovada por padrão físico, sem propagar semântica de um
    # cabeçalho tardio para registros que originalmente não tinham cabeçalho.
    preenchidos = [b for b in blocos if b['linhas']]
    # Cabeçalhos tardios podem oferecer evidência semântica para outras
    # regiões somente quando as colunas transacionais se mantêm compatíveis.
    evidencias_cabecalho_tardio = []
    indices_transacionais = [item['linha'] - 1 for item in auditoria if item.get('tipo') == 'transacao']
    candidatos_cabecalho = [
        (indice, nomes, confianca)
        for indice, (nomes, confianca) in cabecalhos.items()
    ]
    linhas_cabecalho_auditadas = {indice for indice, _, _ in candidatos_cabecalho}
    candidatos_cabecalho.extend(
        (item['linha'] - 1, item.get('valores', []), 100.0)
        for item in auditoria
        if item.get('tipo') == 'cabecalho' and item.get('linha', 0) > 20
        and item.get('linha', 0) - 1 not in linhas_cabecalho_auditadas
    )
    for indice, nomes_cabecalho, confianca_cabecalho in candidatos_cabecalho:
        anteriores = [i for i in indices_transacionais if i < indice]
        posteriores = [i for i in indices_transacionais if i > indice]
        if indice < 20 or len(anteriores) < 10 or len(posteriores) < 10:
            continue
        compatibilidades = []
        colunas_compativeis = []
        for coluna, nome in enumerate(nomes_cabecalho):
            antes = [assinaturas[i][coluna] for i in anteriores if coluna < len(assinaturas[i]) and assinaturas[i][coluna] != '_']
            depois = [assinaturas[i][coluna] for i in posteriores if coluna < len(assinaturas[i]) and assinaturas[i][coluna] != '_']
            if not depois:
                continue
            tipo_depois = Counter(depois).most_common(1)[0][0]
            taxa_depois = depois.count(tipo_depois) / len(depois)
            opcional = not antes
            tipo_antes = Counter(antes).most_common(1)[0][0] if antes else None
            taxa_antes = antes.count(tipo_antes) / len(antes) if antes else 1.0
            compativel = opcional or tipo_antes == tipo_depois
            if not opcional:
                compatibilidades.append(min(taxa_antes, taxa_depois) if compativel else 0.0)
            colunas_compativeis.append({
                'posicao': coluna + 1,
                'rotulo': seguro(nome),
                'tipo_antes': tipo_antes,
                'tipo_depois': tipo_depois,
                'opcional_na_regiao_anterior': opcional,
                'taxa_tipo_antes': round(taxa_antes, 4),
                'taxa_tipo_depois': round(taxa_depois, 4),
                'compativel': bool(compativel and taxa_depois >= 0.9 and (opcional or taxa_antes >= 0.9)),
            })
        taxa = sum(compatibilidades) / len(compatibilidades) if compatibilidades else 0.0
        campos_core = [item for item in colunas_compativeis if not item['opcional_na_regiao_anterior']]
        taxa_campos_compativeis = sum(item['compativel'] for item in campos_core) / max(1, len(campos_core))
        # Admite uma coluna incompatível isolada como ambígua, sem propagar o
        # rótulo dela. Se a maioria da estrutura mudar, nenhuma propagação ocorre.
        valido = len(campos_core) >= 3 and taxa_campos_compativeis >= 0.8
        for item in colunas_compativeis:
            item['mapeamento_permitido'] = bool(valido and item['compativel'])
            confianca_campo = min(
                confianca_cabecalho,
                item.get('taxa_tipo_antes', 1.0) * 100,
                item.get('taxa_tipo_depois', 1.0) * 100,
            )
            item['confianca'] = round(confianca_campo, 2) if item['mapeamento_permitido'] else 0.0
        evidencias_cabecalho_tardio.append({
            'linha': indice + 1,
            'cabecalho_repetido': sum(1 for nomes, _ in cabecalhos.values() if nomes == nomes_cabecalho) > 1,
            'linhas_transacionais_anteriores': len(anteriores),
            'linhas_transacionais_posteriores': len(posteriores),
            'compatibilidade_estrutural': round(taxa * 100, 2),
            'validado': bool(valido),
            'origem': 'cabecalho_repetido' if sum(1 for nomes, _ in cabecalhos.values() if nomes == nomes_cabecalho) > 1 else 'cabecalho_posterior',
            'colunas': colunas_compativeis,
        })
    continuacao = forte and len(preenchidos) > 1 and any(not b['nomes'] for b in preenchidos)
    cabecalhos_reais = {tuple(str(v).strip() for v in b['nomes']) for b in preenchidos if b['nomes']}
    if continuacao and len(cabecalhos_reais) <= 1:
        blocos = [{'nomes': [], 'linhas': [r for b in preenchidos for r in b['linhas']], 'indices': [i for b in preenchidos for i in b['indices']], 'cabecalho': None, 'confianca': 0}]

    contagem = Counter(item['tipo'] for item in auditoria)
    meta = {
        'estrutura_detectada': 'relatorio_operacional', 'origem': origem,
        'linhas_originais': len(linhas), 'registros_extraidos': contagem['transacao'],
        'linhas_resumo': sum(contagem[t] for t in ('meta', 'subtotal', 'total', 'resumo')),
        'linhas_periodo': contagem['periodo'], 'linhas_vazias': contagem['vazia'],
        'linhas_desconhecidas': contagem['desconhecida'],
        'percentual_linhas_reconhecidas': round(100 * (len(linhas) - contagem['desconhecida']) / max(1, len(linhas)), 2),
        'percentual_linhas_desconhecidas': round(100 * contagem['desconhecida'] / max(1, len(linhas)), 2),
        'confianca_estrutural': round(100 * contagem['transacao'] / max(1, contagem['transacao'] + contagem['desconhecida']), 2),
        'linhas_separadas': len(linhas) - contagem['transacao'], 'auditoria_linhas': auditoria,
        'resumos': [r for r in auditoria if r['tipo'] in ('meta', 'total', 'subtotal', 'resumo')],
        'evidencias_excel': evidencias, 'transformacoes': compostos,
        'formulas_indisponiveis': formulas_indisponiveis,
        'blocos_transacionais': repeticao['perfis'],
        'assinatura_dominante': ['I' if c in repeticao['ids'] else t for c, t in enumerate(repeticao['dominante'])],
        'posicoes_identificadores_provaveis': [c + 1 for c in repeticao['ids']],
        'compatibilidade_estrutural': repeticao['compatibilidade'],
        'confianca_bloco_transacional': min((p['compatibilidade'] for p in repeticao['perfis'] if p['forte']), default=0),
        'linhas_com_conteudo': len(linhas) - contagem['vazia'],
        'colunas_vazias_ignoradas_assinatura': [i + 1 for i in range(bruto.shape[1]) if i not in ativos],
        'blocos': [{'id': f'bloco_{i + 1}', 'linha_cabecalho': b['cabecalho'], 'linhas_origem': b['indices'], 'nomes_originais': [seguro(v) for v in b['nomes']]} for i, b in enumerate(blocos) if b['linhas']],
        'evidencias_cabecalho_tardio': evidencias_cabecalho_tardio,
    }
    resultado = []
    for bloco in blocos:
        if not bloco['linhas']:
            continue
        df = pd.DataFrame(bloco['linhas']).infer_objects()
        nomes = bloco['nomes']
        # Marcador só sai quando todos os valores preenchidos são moedas e há
        # uma única coluna vizinha numérica compatível. Não infere a métrica.
        for c in list(df.columns):
            if c not in df:
                continue
            preenchidos = [v for v in df[c] if not vazio(v)]
            if not preenchidos or not all(str(v).strip() in MOEDAS for v in preenchidos):
                continue
            candidatos = [viz for viz in (c - 1, c + 1) if viz in df and all(vazio(v) or numero(v) is not None for v in df[viz]) and df[viz].notna().any()]
            if len(candidatos) > 1:
                explicitos = [viz for viz in candidatos if any(isinstance(v, str) and (',' in v or '.' in v) for v in df[viz] if not vazio(v))]
                if len(explicitos) == 1:
                    candidatos = explicitos
            if len({str(v).strip() for v in preenchidos}) > 1:
                meta['revisao_necessaria'] = True
            if len(candidatos) != 1:
                meta['revisao_necessaria'] = True
                continue
            viz = candidatos[0]
            antes = [seguro(v) for v in df[viz]]
            marcadores = [seguro(v) for v in df[c]]
            df[viz] = df[viz].map(lambda v: numero(v) if not vazio(v) else None)
            df = df.drop(columns=c)
            meta['transformacoes'].append({'tipo': 'marcador_monetario', 'coluna_original': c + 1, 'valor_coluna_original': viz + 1, 'linhas': bloco['indices'], 'valores_originais': antes, 'marcadores_originais': marcadores})
        for c in df.columns:
            preenchidos = [v for v in df[c] if not vazio(v)]
            monetarios = any(isinstance(v, str) and numero(v) is not None and (any(m in v for m in MOEDAS) or (v.strip().startswith('(') and v.strip().endswith(')')) or (',' in v and '.' in v)) for v in preenchidos)
            if monetarios:
                if all(numero(v) is not None for v in preenchidos):
                    meta['transformacoes'].append({'tipo': 'valores_monetarios', 'coluna_original': c + 1, 'linhas': bloco['indices'], 'valores_originais': [seguro(v) for v in df[c]]})
                    df[c] = df[c].map(lambda v: numero(v) if not vazio(v) else None)
                else:
                    meta['revisao_necessaria'] = True
        restantes = list(df.columns)
        diag = {'cabecalho_detectado': bloco['cabecalho'] is not None, 'linha_cabecalho': bloco['cabecalho'], 'confianca_cabecalho': bloco['confianca'], 'linhas_vazias_removidas': 0}
        df = preparar_tabela(df.reset_index(drop=True), [nomes[c] if c < len(nomes) else f'coluna_{c + 1}' for c in restantes], diag)
        if diag['colunas_renomeadas'] or diag['colunas_vazias_removidas']:
            meta['transformacoes'].append({'tipo': 'preparacao_colunas', 'renomeadas': diag['colunas_renomeadas'], 'colunas_vazias_removidas': diag['colunas_vazias_removidas']})
        resultado.append(df)
    if meta.get('revisao_necessaria'):
        meta['status'] = 'review_required'
        if not meta.get('motivos'):
            meta['motivos'] = ['A preparation step found unresolved structural ambiguity.']
        meta['motivo'] = '; '.join(meta['motivos'])
    meta['quantidade_blocos'] = len(resultado)
    linhas_conteudo = max(1, meta['linhas_com_conteudo'])
    desconhecidos = [r for r in auditoria if r['tipo'] == 'desconhecida']
    reconhecidas = sum(contagem[t] for t in ('transacao', 'meta', 'total', 'subtotal', 'resumo', 'periodo', 'cabecalho', 'cabecalho_superior', 'titulo', 'comentario', 'separador'))
    cobertura = 100 * reconhecidas / linhas_conteudo
    cobertura_transacoes = 100 * contagem['transacao'] / linhas_conteudo
    taxa_unknown = len(desconhecidos) / linhas_conteudo
    meta['cobertura_classificada'] = round(cobertura, 2)
    meta['coverage_transaction_rows'] = round(cobertura_transacoes, 2)
    meta['confidence_transaction_structure'] = round(repeticao['compatibilidade'], 2) if forte else 0
    meta['confidence_file'] = round(100 * (1 - taxa_unknown), 2)
    meta['linhas_nao_transacionais_reconhecidas'] = reconhecidas - contagem['transacao']
    meta['unknown_regions'] = []
    for item in desconhecidos:
        if not meta['unknown_regions'] or item['linha'] > meta['unknown_regions'][-1]['fim'] + 1:
            meta['unknown_regions'].append({'inicio': item['linha'], 'fim': item['linha'], 'quantidade': 1, 'exemplos': []})
        else:
            regiao = meta['unknown_regions'][-1]
            regiao['fim'] = item['linha']
            regiao['quantidade'] += 1
        if len(meta['unknown_regions'][-1]['exemplos']) < 3:
            meta['unknown_regions'][-1]['exemplos'].append(item.get('valores', [])[:5])
    # A strong dominant family can be analyzed while a small ambiguous
    # portion remains excluded from the dataset and preserved in the audit.
    partial_seguro = bool(
        forte and contagem['transacao'] >= 20
        and repeticao['compatibilidade'] >= 95
        and not repeticao['incompativeis']
        and taxa_unknown <= 0.15
    )
    residuais = partial_seguro
    meta['residuais_preservados'] = bool(desconhecidos and residuais)
    meta['revisao_necessaria'] = bool(meta.get('revisao_necessaria') or repeticao['incompativeis'] or (desconhecidos and not residuais))
    meta['status'] = 'review_required' if meta['revisao_necessaria'] else 'partial' if desconhecidos else 'accepted'
    meta['motivos'] = []
    if repeticao['incompativeis']:
        meta['motivos'].append('Incompatible transaction families were found.')
    if desconhecidos and not residuais:
        meta['motivos'].append('Ambiguous rows exceed the safe partial-preservation limit.')
    if not forte and contagem['transacao'] >= 20:
        meta['motivos'].append('No dominant transaction signature reached sufficient consistency.')
    meta['motivo'] = '; '.join(meta['motivos']) or ('Rows were extracted partially; unknown rows remain in the audit.' if desconhecidos else 'Rows were extracted with a consistent structure.')
    meta['blocos_detectados'] = []
    for bloco in blocos:
        if not bloco['indices']:
            continue
        idxs = bloco['indices']
        padrao = repeticao['ajustadas'][idxs[0] - 1] if idxs else ()
        meta['blocos_detectados'].append({
            'start_row': min(idxs), 'end_row': max(idxs),
            'classification': 'transactional',
            'transaction_rows': len(idxs),
            'coverage': round(100 * len(idxs) / max(1, max(idxs) - min(idxs) + 1), 2),
            'confidence': round(repeticao['compatibilidade'], 2) if forte else 0,
            'dominant_signature': ['I' if c in repeticao['ids'] else t for c, t in enumerate(padrao)],
        })
    for df in resultado:
        df.attrs['ingestao']['normalizacao'] = meta
    return {'aplicado': True, 'blocos': resultado, 'metadados': meta}
