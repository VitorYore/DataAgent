"""Achados determinísticos sobre agregados existentes, sem acessar o DataFrame."""

import hashlib
import json
import math

from src.analytics.temporal_comparison import comparar_serie, magnitude_referencia


LABELS = {"faturamento": "Faturamento", "valor_total": "Valor Total",
          "valor_com_desconto": "Valor com Desconto", "lucro": "Lucro",
          "margem_bruta": "Margem Bruta", "custo": "Custo"}
MIN_POPULACAO = 10
COBERTURA_ALTA = 0.95
TOP5_MEDIO = 50
TOP5_ALTO = 80
PERDA_MEDIA = 0.05
PERDA_ALTA = 0.20
PRIORIDADES = {
    "high": {"high": "high", "medium": "medium", "low": "medium"},
    "medium": {"high": "medium", "medium": "medium", "low": "low"},
    "low": {"high": "low", "medium": "low", "low": "low"},
}
ORDEM = {"high": 0, "medium": 1, "low": 2}


def numero_valido(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def identificar_achado(analysis_id, rule, metric, scope, entity=None, period=None, comparison=None):
    identidade = None
    if entity:
        identidade = entity.get("id") if entity.get("id") is not None else entity.get("value")
    # Valores e textos podem mudar sem mudar a identidade do evento.
    referencia = comparison.get("reference") if comparison else None
    key = [analysis_id, rule, metric, scope, identidade, period, referencia]
    payload = json.dumps(key, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return "finding-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def deduplicar_achados(findings):
    ordered = sorted(findings, key=lambda item: (
        ORDEM[item["priority"]], ORDEM[item["impact"]], ORDEM[item["confidence"]], item["id"]))
    unique = {}
    for item in ordered:
        unique.setdefault(item["id"], item)
    return list(unique.values())


def _evidencia(name, value, source, metric, unit=None, **extra):
    return {"name": name, "value": value, "unit": unit, "source": source,
            "concept": metric, **extra}


def _confianca(stats, metric, scope):
    reasons = [f"Métrica identificada como {LABELS[metric]}; descreve valores informados."]
    confidence = "high"
    rows, valid, population = (stats.get(k) for k in ("registros", "registros_validos", "populacao"))
    if not numero_valido(rows) or rows <= 0 or not numero_valido(valid):
        confidence = "medium"
        reasons.append("Cobertura da população não documentada neste resultado.")
    elif valid / rows < COBERTURA_ALTA:
        confidence = "low"
        reasons.append("Menos de 95% dos registros têm os campos necessários preenchidos.")
    else:
        reasons.append("Ao menos 95% dos registros têm os campos necessários preenchidos.")
    if not numero_valido(population):
        confidence = "low"
        reasons.append("População com métrica válida desconhecida.")
    elif population < MIN_POPULACAO:
        confidence = "low"
        reasons.append("População com menos de 10 observações; interpretação restrita.")
    if scope == "customers" and not stats.get("identidade_por_id"):
        if confidence == "high":
            confidence = "medium"
        reasons.append("Identidade baseada em nomes; variantes podem representar a mesma entidade.")
    return confidence, reasons


def _achado(analysis_id, rule, metric, scope, summary, impact, stats, evidence, recommendation):
    confidence, reasons = _confianca(stats, metric, scope)
    return {
        "id": identificar_achado(analysis_id, rule, metric, scope),
        "rule": rule, "rule_version": 1, "type": rule,
        "title": "Participação dos principais clientes" if rule == "customer_concentration"
        else f"Resultados negativos de {LABELS[metric]}",
        "summary": summary, "metric": metric, "metric_label": LABELS[metric], "unit": None,
        "scope": scope, "entity": None, "impact": impact,
        "confidence": confidence, "confidence_reasons": reasons,
        "priority": PRIORIDADES[impact][confidence], "evidence": evidence,
        "period": None, "comparison": None, "recommendation": recommendation,
    }


def _evidencias_populacao(stats, source, metric):
    return [_evidencia(key, stats[key], f"{source}.{key}", metric, "count")
            for key in ("registros", "registros_validos", "populacao")
            if numero_valido(stats.get(key))]


def _concentracao(clientes, analysis_id):
    metric = (clientes.get("metrica_principal") or {}).get("conceito")
    if metric not in ("faturamento", "valor_total", "valor_com_desconto"):
        return None
    stats = clientes.get("evidencias_metricas", {}).get(metric, {})
    total, top1, top5 = (stats.get(k) for k in ("total_metrica", "top1_valor", "top5_valor"))
    population = stats.get("populacao")
    if not all(numero_valido(v) for v in (total, top1, top5, population)):
        return None
    if total <= 0 or population <= 0 or not 0 <= top1 <= top5 <= total + 0.005:
        return None
    # Valores negativos tornam a participação no saldo líquido inadequada para esta regra.
    if stats.get("registros_negativos") != 0:
        return None
    share = top5 / total * 100
    impact = "low"
    if population >= MIN_POPULACAO:
        impact = "high" if share >= TOP5_ALTO else "medium" if share >= TOP5_MEDIO else "low"
    source = f"clientes.evidencias_metricas.{metric}"
    evidence = _evidencias_populacao(stats, source, metric)
    for name in ("total_metrica", "top1_valor", "top5_valor"):
        evidence.append(_evidencia(name, stats[name], f"{source}.{name}", metric))
    leader = clientes.get(f"maior_{metric}")
    if leader:
        evidence.append(_evidencia("maior_cliente", {"id": leader.get("cliente_id"),
                         "value": leader.get("cliente")}, f"clientes.maior_{metric}", metric))
    for name, numerator in (("top1_percentual", top1), ("top5_percentual", top5)):
        evidence.append(_evidencia(name, numerator / total * 100, source, metric, "%",
                                   numerator=numerator, denominator=total))
    evidence.append(_evidencia("criterios_impacto", {"populacao_minima": MIN_POPULACAO,
                    "top5_medium": TOP5_MEDIO, "top5_high": TOP5_ALTO}, "customer_concentration.v1", metric))
    label = LABELS[metric]
    percentage_text = f"{share:.2f}".replace(".", ",")
    summary = (f"Os {min(5, int(population))} maiores clientes representam "
               f"{percentage_text}% de {label}, entre {int(population)} clientes com valor válido.")
    finding = _achado(analysis_id, "customer_concentration", metric, "customers", summary,
                   impact, stats, evidence,
                   "Monitorar a participação dos principais clientes e investigar possibilidades de diversificação da carteira."
                   if impact != "low" else None)
    finding["confidence_reasons"].append("Denominador positivo e valores não negativos para a participação.")
    return finding


def _negativos(stats, metric, scope, source, analysis_id):
    count, population, loss, absolute = (stats.get(k) for k in
                                        ("negativos", "populacao", "soma_negativos", "soma_absoluta"))
    if not all(numero_valido(v) for v in (count, population, loss, absolute)):
        return None
    if count <= 0 or population < count or loss >= 0 or absolute < abs(loss) or absolute <= 0:
        return None
    relative = abs(loss) / absolute
    impact = "low"
    if population >= MIN_POPULACAO:
        if count >= 5 and count / population >= PERDA_ALTA and relative >= PERDA_ALTA:
            impact = "high"
        elif count >= 2 and relative >= PERDA_MEDIA:
            impact = "medium"
    evidence = _evidencias_populacao(stats, source, metric)
    for name in ("negativos", "soma_negativos", "soma_absoluta"):
        evidence.append(_evidencia(name, stats[name], f"{source}.{name}", metric,
                                   "count" if name == "negativos" else None))
    evidence.extend([
        _evidencia("participacao_magnitude_negativa", relative * 100, source, metric, "%",
                   numerator=abs(loss), denominator=absolute),
        _evidencia("participacao_populacao_negativa", count / population * 100, source, metric, "%",
                   numerator=count, denominator=population),
        _evidencia("criterios_impacto", {"populacao_minima": MIN_POPULACAO,
                   "medium": {"negativos_minimos": 2, "magnitude_minima": PERDA_MEDIA},
                   "high": {"negativos_minimos": 5, "magnitude_minima": PERDA_ALTA,
                            "abrangencia_minima": PERDA_ALTA}}, "negative_results.v1", metric),
    ])
    noun = "cliente" if scope == "customers" else "registro"
    subject = f"{int(count)} {noun}" + ("s apresentam" if count != 1 else " apresenta")
    adjective = "negativa" if metric == "margem_bruta" else "negativo"
    loss_text = f"{loss:.2f}".replace(".", ",")
    summary = (f"{subject} {LABELS[metric]} {adjective}, em uma população de {int(population)} "
               f"{noun}s com valor válido. Soma dos resultados negativos: {loss_text}.")
    return _achado(analysis_id, "negative_results", metric, scope, summary, impact, stats, evidence,
                   f"Revisar os valores informados de {LABELS[metric]} e investigar os resultados negativos dessa população.")


def gerar_achados_analiticos(clientes=None, desempenho=None, analysis_id=None, temporal=None, crescimento=None,
                           entidades=None):
    clientes, desempenho = clientes or {}, desempenho or {}
    findings = [_concentracao(clientes, analysis_id)]
    for metric in ("lucro", "margem_bruta"):
        stats = clientes.get("evidencias_metricas", {}).get(metric, {})
        findings.append(_negativos(stats, metric, "customers",
                                  f"clientes.evidencias_metricas.{metric}", analysis_id))
    findings.append(_negativos(desempenho.get("evidencias_negativos", {}), "lucro", "records",
                              "desempenho.evidencias_negativos", analysis_id))
    findings.extend(_achados_temporais(temporal or {}, desempenho, crescimento or {}, analysis_id))
    findings.extend(gerar_achados_entidades(entidades or [], analysis_id))
    return deduplicar_achados([item for item in findings if item is not None])


DELTA_ENTIDADE_RELEVANTE = 0.02
DELTA_GLOBAL_CONTRIBUICAO = 0.10
CONTRIBUICAO_MINIMA = 0.10
DELTA_ENTIDADE_ALTO = 0.20
CONTRIBUICAO_ALTA = 30
REGISTROS_ENTIDADE_MINIMOS = 5
LIMITE_ENTIDADES_REGRA_PERIODO = 5
LIMITE_ACHADOS_POR_TIPO = 100


def gerar_achados_entidades(aggregates, analysis_id=None):
    from src.analytics.entity_evolution import comparar_entidades

    selected = []
    for aggregate in aggregates:
        if aggregate["metric"] not in LABELS:
            continue
        for window in comparar_entidades(aggregate):
            candidates = []
            for row in window["rows"]:
                finding = _achado_entidade(row, window, analysis_id)
                if finding:
                    candidates.append(finding)
            counts = {}
            for item in sorted(candidates, key=_ordem_entidade):
                rule = item["rule"]
                if counts.get(rule, 0) < LIMITE_ENTIDADES_REGRA_PERIODO:
                    selected.append(item)
                    counts[rule] = counts.get(rule, 0) + 1
    result, counts = [], {}
    for item in sorted(selected, key=_ordem_entidade):
        kind = item["scope"]
        if counts.get(kind, 0) < LIMITE_ACHADOS_POR_TIPO:
            result.append(item)
            counts[kind] = counts.get(kind, 0) + 1
    return deduplicar_achados(result)


def _ordem_entidade(item):
    return (ORDEM[item["priority"]], ORDEM[item["impact"]],
            -abs(item["comparison"]["absolute_change"]), item["id"])


def _achado_entidade(row, window, analysis_id):
    comparison = row["comparison"]
    delta = comparison["absolute_change"]
    global_comparison = window["global_comparison"]
    global_delta = global_comparison["absolute_change"]
    scale = max(window["reference"], global_comparison["reference_magnitude"] or 0)
    if scale <= 0 or abs(delta) / scale < DELTA_ENTIDADE_RELEVANTE:
        return None
    metric, kind = window["metric"], window["entity_type"]
    entity = row["entity"]
    direction = "growth" if delta > 0 else "decline"
    same_direction = delta * global_delta > 0
    contribution = delta / global_delta * 100 if same_direction else None
    contributor = (same_direction and window["complete_fields"]
                   and abs(global_delta) / scale >= DELTA_GLOBAL_CONTRIBUICAO
                   and contribution >= CONTRIBUICAO_MINIMA * 100)
    prefix = "customer" if kind == "cliente" else "product"
    rule = prefix + ("_contributor_" if contributor else "_") + direction
    scope = "customers" if kind == "cliente" else "products"
    before, after = comparison["previous_period"], comparison["current_period"]
    period = {"start": before, "end": after, "granularity": "M"}
    sufficient = all(row["valid"][p] >= REGISTROS_ENTIDADE_MINIMOS and row["valid"][p] == row["records"][p] for p in (before, after))
    confidence = "medium" if window["complete_fields"] and sufficient else "low"
    reasons = ["População completa consultada; valores observados nos dois períodos consecutivos.",
               "Cobertura do calendário operacional desconhecida; não se presume mês completo.",
               f"Identidade: {entity['identity_source']}; conceito: {LABELS[metric]}."]
    if entity["identity_source"] != "stable_id":
        reasons.append("Identidade textual, mesmo após confirmação de alias, não equivale a ID estável.")
    if not window["complete_fields"] or not sufficient:
        reasons.append("Cobertura de campos inferior a 95%, nulos na entidade ou menos de cinco registros válidos em um período.")
    if not comparison["percentage_valid"]:
        reasons.append(f"Percentual indisponível: {comparison['reason']}; usa-se variação absoluta.")
    impact = "medium"
    if confidence == "medium" and (abs(delta) / scale >= DELTA_ENTIDADE_ALTO or (contributor and contribution >= CONTRIBUICAO_ALTA)):
        impact = "high"
    label, name = LABELS[metric], entity["label"]
    movement = "aumento" if delta > 0 else "redução"
    observed = "observado" if delta > 0 else "observada"
    amount = f"{abs(delta):.2f}".replace(".", ",")
    summary = f"{name}: {movement} {observed} de {amount} em {label}, entre {before} e {after}."
    if contributor:
        pct = f"{contribution:.2f}".replace(".", ",")
        summary += f" Equivale a {pct}% da variação líquida global; outras entidades podem compensar esse movimento."
    gross = window["gross_positive_change_matched" if delta > 0 else "gross_negative_change_matched"]
    details = {"entity_id": entity["id"], "entity_label": name, "entity_type": kind,
               "identity_source": entity["identity_source"], "comparison": comparison,
               "previous_share": row["previous_share"], "current_share": row["current_share"],
               "share_denominators": {before: global_comparison["previous_value"], after: global_comparison["current_value"]},
               "global_change": global_delta, "contribution": contribution,
               "contribution_denominator": global_delta if same_direction else None,
               "gross_negative_change_matched": window["gross_negative_change_matched"],
               "gross_positive_change_matched": window["gross_positive_change_matched"],
               "share_of_gross_direction_matched": abs(delta) / gross * 100 if gross else None,
               "gross_denominator": gross, "unexplained_by_matched_pairs": window["unexplained_by_matched_pairs"],
               "coverage": window["coverage"], "entity_records": row["records"], "entity_valid": row["valid"],
               "absences": window["absences"], "materiality": {"numerator": abs(delta), "denominator": scale,
               "minimum_entity_ratio": DELTA_ENTIDADE_RELEVANTE, "minimum_global_ratio": DELTA_GLOBAL_CONTRIBUICAO,
               "minimum_contribution_ratio": CONTRIBUICAO_MINIMA,
               "high_entity_ratio": DELTA_ENTIDADE_ALTO, "high_contribution_percent": CONTRIBUICAO_ALTA,
               "minimum_valid_records": REGISTROS_ENTIDADE_MINIMOS}}
    return {"id": identificar_achado(analysis_id, rule, metric, scope, entity=entity, period=period),
            "rule": rule, "rule_version": 1, "type": rule, "title": f"{movement.capitalize()} {observed} por {kind}",
            "summary": summary, "metric": metric, "metric_label": label, "unit": None, "scope": scope,
            "entity": entity, "impact": impact, "confidence": confidence, "confidence_reasons": reasons,
            "priority": PRIORIDADES[impact][confidence], "period": period, "comparison": comparison,
            "evidence": [_evidencia("evolucao_entidade", details, "entity_evolution.population", metric)],
            "recommendation": f"Investigar a variação observada de {label} associada a {name} e conferir a cobertura dos períodos."}


DELTA_TEMPORAL_RELEVANTE = 0.20
DELTA_TEMPORAL_ALTO = 0.50


def _achados_temporais(temporal, desempenho, crescimento, analysis_id):
    series = []
    metric = temporal.get("metrica")
    if metric in LABELS:
        series.append((metric, temporal.get("valores_mensais_precisos", temporal.get("valores_mensais", {})), temporal.get("comparacoes"),
                       temporal.get("registros_por_periodo", {}), temporal.get("cobertura", {}),
                       "analise_temporal", temporal.get("granularidade", "M")))
    if metric != "lucro" and desempenho.get("lucro_mensal"):
        series.append(("lucro", desempenho.get("lucro_mensal_preciso", desempenho["lucro_mensal"]),
                       crescimento.get("lucro", {}).get("comparacoes"),
                       desempenho.get("registros_por_periodo", {}), desempenho.get("cobertura_temporal", {}),
                       "desempenho.lucro_mensal", "M"))
    findings = []
    for concept, values, comparisons, counts, coverage, source, granularity in series:
        if len(values) < 2:
            continue
        comparisons = comparar_serie(values, granularity) if comparisons is None else comparisons
        reference = magnitude_referencia(values.values())
        for comparison in comparisons:
            finding = _achado_temporal(concept, comparison, reference, len(values), counts,
                                       coverage, source, analysis_id)
            if finding:
                findings.append(finding)
    return findings


def _achado_temporal(metric, comparison, reference, observations, counts, coverage, source, analysis_id):
    delta = comparison["absolute_change"]
    if not comparison["comparable"] or not comparison["continuous"] or delta is None or delta == 0:
        return None
    scale = max(reference, comparison["reference_magnitude"] or 0)
    if scale <= 0 or abs(delta) / scale < DELTA_TEMPORAL_RELEVANTE:
        return None
    before, after = comparison["previous_period"], comparison["current_period"]
    percentage = comparison["percentage_change"]
    rows, valid = coverage.get("registros_entrada"), coverage.get("registros_validos")
    covered = numero_valido(rows) and rows > 0 and numero_valido(valid) and valid / rows >= COBERTURA_ALTA
    sufficient = all(numero_valido(counts.get(p)) and counts[p] >= 5 for p in (before, after))
    confidence = "medium" if covered and sufficient and observations >= 3 else "low"
    reasons = [f"Conceito preservado: {LABELS[metric]}; períodos consecutivos.",
               "Cobertura do calendário operacional desconhecida; não se presume período completo."]
    if not covered:
        reasons.append("Cobertura dos campos inferior a 95% ou desconhecida.")
    if not sufficient or observations < 3:
        reasons.append("Menos de três períodos ou contagem inferior a cinco/desconhecida em um dos períodos comparados.")
    if not comparison["percentage_valid"]:
        reasons.append(f"Percentual indisponível: {comparison['reason']}; conclusão baseada no delta absoluto.")
    impact = "medium"
    if (covered and sufficient and observations >= 3 and percentage is not None
            and abs(percentage) >= 20 and abs(delta) / scale >= DELTA_TEMPORAL_ALTO):
        impact = "high"
    direction = comparison["direction"]
    rule = "temporal_growth" if direction == "increase" else "temporal_decline"
    label = LABELS[metric]
    movement = "aumentou" if direction == "increase" else "diminuiu"
    amount = f"{abs(delta):.2f}".replace(".", ",")
    suffix = (f" ({abs(percentage):.2f}%)".replace(".", ",") if percentage is not None
              else "; percentual indisponível")
    summary = f"{label} {movement} {amount} entre {before} e {after}{suffix}."
    window = {"start": before, "end": after, "granularity": comparison["granularity"]}
    evidence = [
        _evidencia("comparacao", comparison, source, metric),
        _evidencia("materialidade_absoluta", abs(delta) / scale, source, metric, "ratio",
                   numerator=abs(delta), denominator=scale),
        _evidencia("registros_por_periodo", {before: counts.get(before), after: counts.get(after)}, source, metric, "count"),
        _evidencia("cobertura", coverage, source, metric),
        _evidencia("periodos_observados", observations, source, metric, "count"),
        _evidencia("limiares_materialidade", {"relevante": DELTA_TEMPORAL_RELEVANTE,
                    "alto": DELTA_TEMPORAL_ALTO, "percentual_alto": 20}, rule + ".v1", metric),
    ]
    return {
        "id": identificar_achado(analysis_id, rule, metric, "temporal", period=window),
        "rule": rule, "rule_version": 1, "type": rule, "metric": metric, "metric_label": label,
        "title": f"{'Aumento' if direction == 'increase' else 'Redução'} relevante de {label}",
        "summary": summary, "unit": None, "scope": "temporal", "entity": None,
        "impact": impact, "confidence": confidence, "confidence_reasons": reasons,
        "priority": PRIORIDADES[impact][confidence], "evidence": evidence,
        "period": window, "comparison": comparison,
        "recommendation": f"Investigar os componentes da variação observada de {label} e conferir a cobertura dos períodos.",
    }
