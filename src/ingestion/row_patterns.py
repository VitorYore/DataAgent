"""Evidência estrutural local, independente de nomes e significado de métricas."""
from collections import Counter, defaultdict
import re


def compatibilidade(assinatura, referencia):
    usados = [i for i, t in enumerate(referencia) if t not in ('_', '$')]
    presentes = [i for i in usados if assinatura[i] != '_']
    if len(presentes) < max(2, len(usados) * 0.6):
        return 0.0
    return sum(assinatura[i] == referencia[i] for i in presentes) / len(presentes)


def inspecionar_padrao(linhas, assinaturas, tipos, formulas):
    """Retorna evidências; não escolhe colunas de negócio ou calcula fórmulas.

    Vinte registros e 95% de compatibilidade são exigidos para o caminho novo.
    O caminho antigo para tabelas pequenas continua existindo separadamente.
    """
    por_linha = defaultdict(list)
    por_coluna = defaultdict(list)
    for f in formulas:
        por_linha[f['linha'] - 1].append(f)
        por_coluna[f['coluna'] - 1].append(f)
    opcionais = {c for c, fs in por_coluna.items() if len(fs) >= 20 and sum(not f.get('sem_cache') for f in fs) / len(fs) >= 0.95}
    ajustadas = []
    for i, sig in enumerate(assinaturas):
        s = list(sig)
        for f in por_linha[i]:
            if f.get('sem_cache') and f['coluna'] - 1 in opcionais:
                s[f['coluna'] - 1] = '_'
        ajustadas.append(tuple(s))
    candidatos = [i for i, s in enumerate(ajustadas) if tipos[i] is None and sum(t not in ('_', '$') for t in s) >= 3 and ('D' in s or (s.count('N') >= 2 and s.count('T') >= 1))]
    frequencias = Counter(ajustadas[i] for i in candidatos)
    dominante, frequencia = frequencias.most_common(1)[0] if frequencias else ((), 0)
    iguais = [i for i in candidatos if dominante and compatibilidade(ajustadas[i], dominante) >= 0.95]
    ids = []
    if len(iguais) >= 20:
        for c, t in enumerate(dominante):
            if t != 'N':
                continue
            valores = [linhas[i][c] for i in iguais if ajustadas[i][c] == 'N']
            try:
                nums = [float(v) for v in valores]
                if len(nums) >= 20 and all(n.is_integer() for n in nums) and len(set(nums)) / len(nums) >= 0.95:
                    ids.append(c)
            except (ValueError, TypeError):
                pass
    datas = [c for c, t in enumerate(dominante) if t == 'D']
    fortes = set()
    perfis, grupo = [], []

    def fechar():
        if not grupo:
            return
        contagem = Counter(ajustadas[i] for i in grupo)
        padrao, n = contagem.most_common(1)[0]
        compativeis = [i for i in grupo if compatibilidade(ajustadas[i], padrao) >= 0.95]
        confianca = len(compativeis) / len(grupo)
        forte = len(compativeis) >= 20 and confianca >= 0.95
        if forte:
            fortes.update(compativeis)
        perfis.append({'inicio': grupo[0] + 1, 'fim': grupo[-1] + 1, 'linhas_candidatas': len(grupo), 'linhas_compativeis': len(compativeis), 'compatibilidade': round(confianca * 100, 2), 'assinatura': list(padrao), 'forte': forte})
        grupo.clear()

    candidatos_set = set(candidatos)
    for i, tipo in enumerate(tipos):
        if tipo in ('periodo', 'cabecalho', 'total', 'subtotal', 'resumo', 'meta'):
            fechar()
        if i in candidatos_set:
            grupo.append(i)
        elif por_linha[i] and any(re.search(r'\b(?:SUM|SUBTOTAL|AVERAGE|COUNT|MIN|MAX)\s*\([^)]*:', str(f['formula']), re.I) for f in por_linha[i]) and 'D' not in assinaturas[i]:
            fechar()
    fechar()
    incompativeis = [p for p in perfis if p['forte'] and dominante and compatibilidade(p['assinatura'], dominante) < 0.95]
    sequencias = 1 + sum(atual - anterior > 1 for anterior, atual in zip(iguais, iguais[1:])) if iguais else 0
    taxa_dominante = len(iguais) / max(1, len(candidatos))
    campos_dominantes = sum(tipo not in ('_', '$') for tipo in dominante)
    forte_global = bool(
        len(iguais) >= 20
        and taxa_dominante >= 0.95
        and campos_dominantes >= 3
        and sequencias >= 2
        and not incompativeis
    )
    if forte_global:
        fortes.update(iguais)
    return {'dominante': dominante, 'ids': ids, 'datas': datas, 'ajustadas': ajustadas,
            'fortes': fortes, 'opcionais': opcionais, 'formulas_por_linha': por_linha,
            'incompativeis': incompativeis, 'perfis': perfis,
            'compatibilidade': round(taxa_dominante * 100, 2),
            'linhas_compativeis': len(iguais), 'candidatos': len(candidatos),
            'sequencias_estruturais': sequencias, 'forte_global': forte_global}
