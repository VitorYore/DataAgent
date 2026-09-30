"""Seleção executiva sobre findings prontos, sem recalcular analytics."""

import json

from src.analytics.findings import ORDEM, deduplicar_achados, numero_valido


LIMITE_EXECUTIVO = 8
LIMITE_BAIXO_IMPACTO = 2
LIMITE_BAIXA_CONFIANCA = 2


def familia_achado(item):
    rule = item["rule"]
    if rule == "customer_concentration":
        return "concentracao"
    if rule == "negative_results":
        return "resultados_negativos"
    if rule.startswith("temporal_"):
        return "temporal"
    return {"customers": "clientes", "products": "produtos"}.get(item["scope"], "outros")


def materialidade_achado(item):
    """Lê razões já documentadas; não compara moedas ou deltas de conceitos distintos."""
    for evidence in item.get("evidence", []):
        name, value = evidence.get("name"), evidence.get("value")
        if name == "materialidade_absoluta" and numero_valido(value):
            return abs(value)
        if name in ("top5_percentual", "participacao_magnitude_negativa") and numero_valido(value):
            return abs(value) / 100
        if name == "evolucao_entidade" and isinstance(value, dict):
            materiality = value.get("materiality", {})
            numerator, denominator = materiality.get("numerator"), materiality.get("denominator")
            if numero_valido(numerator) and numero_valido(denominator) and denominator > 0:
                return abs(numerator) / denominator
    return None


def _faixa(item):
    return tuple(ORDEM[item[key]] for key in ("priority", "impact", "confidence"))


def _ordem(item):
    materiality = materialidade_achado(item)
    return (*_faixa(item), materiality is None, -(materiality or 0), item["id"])


def _evento(item):
    # Individual e contribuinte da mesma entidade/janela são a única sobreposição adicional.
    rule = item["rule"].replace("_contributor_", "_")
    entity = item.get("entity") or {}
    identity = entity.get("id") if entity.get("id") is not None else entity.get("value")
    key = [rule, item["metric"], item["scope"], identity, item.get("period"),
           (item.get("comparison") or {}).get("reference")]
    return json.dumps(key, sort_keys=True, ensure_ascii=False)


def selecionar_achados_principais(findings, limite=LIMITE_EXECUTIVO):
    limit = max(0, min(limite, LIMITE_EXECUTIVO))
    # Empates do mesmo ID também independem da ordem incidental de entrada.
    ordered = sorted(findings or [], key=lambda f: json.dumps(f, sort_keys=True, ensure_ascii=False))
    candidates = deduplicar_achados(ordered)
    events = {}
    for item in sorted(candidates, key=lambda f: ("_contributor_" not in f["rule"], _ordem(f))):
        events.setdefault(_evento(item), item)
    candidates = sorted(events.values(), key=_ordem)
    if any(f["impact"] != "low" for f in candidates):
        candidates = [f for f in candidates if f["impact"] != "low"]
    else:
        limit = min(limit, LIMITE_BAIXO_IMPACTO)
    stronger = sum(f["confidence"] != "low" for f in candidates)
    low_limit = min(LIMITE_BAIXA_CONFIANCA, stronger) if stronger else limit
    selected, low_count = [], 0
    for rank in sorted({_faixa(f) for f in candidates}):
        pending = [f for f in candidates if _faixa(f) == rank]
        family_counts = {}
        while pending and len(selected) < limit:
            # Diversidade somente dentro da mesma prioridade, impacto e confiança.
            item = min(pending, key=lambda f: (family_counts.get(familia_achado(f), 0), _ordem(f)))
            pending.remove(item)
            if item["confidence"] == "low" and low_count >= low_limit:
                continue
            family = familia_achado(item)
            family_counts[family] = family_counts.get(family, 0) + 1
            low_count += int(item["confidence"] == "low")
            selected.append({**item, "selection_reason": {
                "priority": item["priority"], "impact": item["impact"], "confidence": item["confidence"],
                "materiality": materialidade_achado(item), "family": family,
                "policy": "diversity_within_same_rank",
            }})
    recommendations = {}
    for item in selected:
        text = " ".join((item.get("recommendation") or "").split()).casefold()
        item["show_recommendation"] = bool(text) and text not in recommendations
        item["recommendation_reference"] = recommendations.get(text) if text else None
        if text:
            recommendations.setdefault(text, item["id"])
    return selected
