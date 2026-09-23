"""Diagnóstico de nomes semelhantes; não modifica dados nem identidade analítica."""
from collections import defaultdict
from difflib import SequenceMatcher
import math
import re
import unicodedata

import pandas as pd

from src.analytics.business import encontrar_coluna_por_papel
from src.analytics.column_mapper import mapear_colunas
from src.analytics.customers import METRICAS_CLIENTE


SIMILARIDADE_MINIMA = 0.92
SIMILARIDADE_ALTA = 0.97
TAMANHO_MINIMO_FUZZY = 10
DIFERENCA_TAMANHO_MAXIMA = 0.12
VIZINHOS_FUZZY = 20
LIMITE_CANDIDATOS = 500
UNIDADES = {"mm", "cm", "m", "km", "g", "kg", "ml", "l"}
SUFIXOS_EMPRESARIAIS = {"ltda", "me", "sa", "eireli"}
TIPOS_ENTIDADE = ("cliente", "produto", "categoria", "loja", "colaborador")


def normalizar_entidade(texto):
    texto = " ".join(str(texto).split()).casefold()
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def explicar_diferenca(left, right):
    reasons = []
    if left != " ".join(left.split()) or right != " ".join(right.split()):
        reasons.append("diferenca_espacamento")
    a, b = " ".join(left.split()), " ".join(right.split())
    if a != b and a.casefold() == b.casefold():
        reasons.append("diferenca_caixa")
    if a.casefold() != b.casefold():
        reasons.append("diferenca_acentuacao")
    return reasons or ["grafia_muito_semelhante"]


def _pares(valores, statistics):
    normalizados = defaultdict(list)
    for value in valores:
        normalized = normalizar_entidade(value)
        if normalized:
            normalizados[normalized].append(value)
    # Uma variante de referência evita listar todos os pares do mesmo grupo.
    for variants in normalizados.values():
        for value in variants[1:]:
            statistics["blocked_pairs"] += 1
            yield variants[0], value, 1.0, explicar_diferenca(variants[0], value)
    blocks = defaultdict(list)
    for text in normalizados:
        if len(text) >= TAMANHO_MINIMO_FUZZY:
            blocks[text[:3]].append(text)
    for texts in blocks.values():
        texts.sort()
        for index, left in enumerate(texts):
            for right in texts[index + 1:index + 1 + VIZINHOS_FUZZY]:
                if abs(len(left) - len(right)) > max(len(left), len(right)) * DIFERENCA_TAMANHO_MAXIMA:
                    continue
                # Números distintos podem identificar produtos/filiais diferentes.
                if re.findall(r"\d+", left) != re.findall(r"\d+", right):
                    continue
                a, b = left.split(), right.split()
                if {t.strip(".,") for t in a} & UNIDADES != {t.strip(".,") for t in b} & UNIDADES:
                    continue
                if (a[-1] in SUFIXOS_EMPRESARIAIS or b[-1] in SUFIXOS_EMPRESARIAIS) and a[-1] != b[-1]:
                    continue
                statistics["blocked_pairs"] += 1
                statistics["fuzzy_comparisons"] += 1
                score = SequenceMatcher(None, left, right, autojunk=False).ratio()
                if score >= SIMILARIDADE_MINIMA:
                    yield normalizados[left][0], normalizados[right][0], score, ["grafia_muito_semelhante"]


def detectar_entidades(df):
    # Evita copiar a auditoria extensa dos attrs em cada agrupamento do perfil.
    df = pd.DataFrame(df, copy=False)
    mapping = mapear_colunas(df)
    roles = {role: encontrar_coluna_por_papel(mapping, role)
             for role in {item.get("papel") for item in mapping.values()}}
    metric = next(({"concept": role, "label": label, "column": roles[role]}
                   for role, label in METRICAS_CLIENTE
                   if roles.get(role) and pd.api.types.is_numeric_dtype(df[roles[role]])), None)
    candidates, stable_ids, statistics, counts_by_type = [], [], {}, {}
    for kind in TIPOS_ENTIDADE:
        column = roles.get(kind)
        if not column:
            continue
        # Também protege IDs explícitos ainda não catalogados pelo mapper (ex.: Categoria_ID).
        id_names = {kind + "_id", "id_" + kind}
        if roles.get(kind + "_id") or any(normalizar_entidade(c).replace(" ", "_") in id_names for c in df.columns):
            stable_ids.append(kind)
            continue
        valid = df[column].map(lambda x: isinstance(x, str) and bool(x.strip()))
        selected = df.loc[valid]
        series = selected[column]
        counts = {value: count for value, count in series.value_counts(sort=False).items() if count > 0}
        n = len(counts)
        stats = {"unique_entities": n, "theoretical_pairs": n * (n - 1) // 2,
                 "blocked_pairs": 0, "fuzzy_comparisons": 0, "candidates": 0}
        statistics[kind] = stats
        grouped = selected.groupby(column, sort=False)
        amounts = grouped[metric["column"]].sum(min_count=1).to_dict() if metric else {}
        orders = grouped[roles["pedido"]].nunique().to_dict() if roles.get("pedido") else {}

        def context(value):
            amount = amounts.get(value)
            return {"value": value, "records": int(counts[value]),
                    "orders": int(orders[value]) if value in orders else None,
                    "metric_value": round(float(amount), 2) if pd.notna(amount) and math.isfinite(float(amount)) else None}

        for left, right, similarity, reasons in _pares(counts, stats):
            stats["candidates"] += 1
            if len(candidates) < LIMITE_CANDIDATOS:
                a, b = context(left), context(right)
                preview = round(a["metric_value"] + b["metric_value"], 2) if a["metric_value"] is not None and b["metric_value"] is not None else None
                candidates.append({"entity_type": kind, "column": column,
                                   "left": a, "right": b, "metric": metric,
                                   "combined_preview": preview, "similarity": round(similarity, 2),
                                   "confidence": "alta" if similarity >= SIMILARIDADE_ALTA else "media",
                                   "reasons": reasons})
        counts_by_type[kind] = stats["candidates"]
    total = sum(counts_by_type.values())
    return {"candidates": candidates, "total_candidates": total,
            "possible_duplicate_entities": counts_by_type, "statistics": statistics,
            "stable_id_types": stable_ids, "truncated": total > len(candidates)}
