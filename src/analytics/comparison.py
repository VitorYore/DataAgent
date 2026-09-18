"""Comparação determinística entre resumos, sempre pela chave semântica exata."""
from datetime import date
import calendar
import math

THRESHOLD_PERCENTUAL = 0.5
LABELS = {
    "faturamento_total": "Faturamento", "lucro_total": "Lucro", "custo_total": "Custo",
    "margem_lucro": "Margem de lucro", "ticket_medio": "Ticket médio",
    "quantidade_pedidos": "Pedidos", "quantidade_registros": "Registros",
    "quantidade_vendida": "Quantidade vendida", "valor_total": "Valor Total",
    "valor_com_desconto": "Valor com Desconto", "margem_bruta": "Margem Bruta",
    "margem_bruta_percentual": "Margem Bruta %",
}
MARGENS = {"margem_lucro", "margem_bruta_percentual"}


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _period(summary):
    points = (summary.get("temporal") or {}).get("serie_temporal") or []
    values = sorted(str(point["periodo"]) for point in points if isinstance(point, dict) and point.get("periodo"))
    return {"start": values[0] if values else None, "end": values[-1] if values else None}


def _days(period):
    def parse(value, is_end):
        text = str(value)
        if len(text) == 7:
            year, month = map(int, text.split("-"))
            day = calendar.monthrange(year, month)[1] if is_end else 1
            return date(year, month, day)
        return date.fromisoformat(text[:10])
    start, end = parse(period["start"], False), parse(period["end"], True)
    return (end - start).days + 1


def _dimension(summary, kind):
    data = summary.get("clientes" if kind == "cliente" else "produtos") or {}
    if kind == "cliente":
        for ranking, metric in (("ranking_valor_total", "valor_total"), ("ranking_faturamento", "faturamento")):
            rows = data.get(ranking) or []
            if rows:
                return rows, metric, "cliente", "cliente_id"
        return [], None, "cliente", "cliente_id"
    rows = data.get("ranking_produtos") or []
    return rows, "faturamento", "produto", "produto_id"


def _compare_dimension(left_summary, right_summary, kind):
    left_rows, left_metric, label_key, id_key = _dimension(left_summary, kind)
    right_rows, right_metric, _, _ = _dimension(right_summary, kind)
    if not left_rows or not right_rows or left_metric != right_metric:
        return None

    def index(rows, metric):
        result = {}
        for row in rows:
            label, identity = row.get(label_key), row.get(id_key)
            key = str(identity) if identity not in (None, "") else str(label or "").strip().casefold()
            amount = _number(row.get(metric))
            if key and amount is not None:
                result[key] = {"label": label, "value": amount, "stable_id": identity not in (None, "")}
        return result

    left, right = index(left_rows, left_metric), index(right_rows, right_metric)
    common, only_left, only_right = [], [], []
    for key in left.keys() | right.keys():
        a, b = left.get(key), right.get(key)
        if a and b:
            common.append({"id": key, "label": b["label"] or a["label"], "left": a["value"], "right": b["value"],
                           "absolute_change": round(b["value"] - a["value"], 2), "identity_reliable": a["stable_id"] and b["stable_id"]})
        elif a:
            only_left.append({"id": key, "label": a["label"], "value": a["value"]})
        else:
            only_right.append({"id": key, "label": b["label"], "value": b["value"]})
    common.sort(key=lambda item: abs(item["absolute_change"]), reverse=True)
    return {"metric": left_metric, "common": common[:5], "only_left": only_left[:5], "only_right": only_right[:5],
            "identity_reliability": "stable_id" if common and all(item["identity_reliable"] for item in common) else "label_or_mixed"}


def comparar_resumos(left_summary, right_summary, left_item, right_item):
    """Compara apenas conceitos presentes e numéricos nos dois resumos."""
    left_kpis, right_kpis = left_summary.get("kpis") or {}, right_summary.get("kpis") or {}
    metrics, insights = {}, []
    for concept in LABELS:
        left, right = _number(left_kpis.get(concept)), _number(right_kpis.get(concept))
        if left is None or right is None:
            continue
        delta = round(right - left, 2)
        percentage = None if left == 0 else round(delta / left * 100, 2)
        direction = "stable" if (abs(percentage) < THRESHOLD_PERCENTUAL if percentage is not None else delta == 0) else ("increase" if delta > 0 else "decrease")
        is_margin = concept in MARGENS
        metrics[concept] = {"concept": concept, "label": LABELS[concept], "left": left, "right": right,
                            "absolute_change": delta, "percentage_change": None if is_margin else percentage,
                            "percentage_point_change": delta if is_margin else None, "direction": direction}
        if direction != "stable":
            variation = f"{percentage:+.2f}%" if percentage is not None and not is_margin else f"{delta:+.2f} pontos percentuais" if is_margin else "sem variação percentual calculável"
            verb = "aumentou" if delta > 0 else "diminuiu"
            insights.append({"category": f"comparison_{concept}", "type": "informativo", "priority": "media",
                             "text": f"{LABELS[concept]} {verb} {variation} entre as análises."})
    left_period, right_period = _period(left_summary), _period(right_summary)
    comparability = "unknown"
    if all(left_period.values()) and all(right_period.values()):
        try:
            left_days, right_days = _days(left_period), _days(right_period)
            ratio = max(left_days, right_days) / max(1, min(left_days, right_days))
            comparability = "same_duration" if left_days == right_days else "similar_duration" if ratio <= 1.1 else "different_duration"
        except ValueError:
            pass
    dimensions = {}
    for kind, key in (("cliente", "clients"), ("produto", "products")):
        result = _compare_dimension(left_summary, right_summary, kind)
        if result:
            dimensions[key] = result
    left_temporal = left_summary.get("temporal") or {}
    right_temporal = right_summary.get("temporal") or {}
    temporal = None
    if left_temporal.get("metrica_principal") and left_temporal.get("metrica_principal") == right_temporal.get("metrica_principal"):
        left_points = {str(point.get("periodo")): _number(point.get("metrica_valor")) for point in left_temporal.get("serie_temporal", []) if isinstance(point, dict)}
        right_points = {str(point.get("periodo")): _number(point.get("metrica_valor")) for point in right_temporal.get("serie_temporal", []) if isinstance(point, dict)}
        shared = sorted(period for period in left_points.keys() & right_points.keys() if left_points[period] is not None and right_points[period] is not None)
        temporal = {"concept": left_temporal["metrica_principal"], "label": left_temporal.get("nome_metrica_principal") or right_temporal.get("nome_metrica_principal"),
                    "left_range": _period(left_summary), "right_range": _period(right_summary),
                    "shared_periods": [{"period": period, "left": left_points[period], "right": right_points[period]} for period in shared]}
    left_quality = left_summary.get("dados") or {}
    right_quality = right_summary.get("dados") or {}
    quality = {key: {"left": left_quality[key], "right": right_quality[key], "absolute_change": right_quality[key] - left_quality[key]}
               for key in ("score_qualidade", "total_valores_nulos", "linhas_duplicadas")
               if isinstance(left_quality.get(key), (int, float)) and isinstance(right_quality.get(key), (int, float))}
    return {"status": "available", "left_analysis": left_item.get("id"), "right_analysis": right_item.get("id"),
            "analyses": {"left": left_item, "right": right_item}, "periods": {"left": left_period, "right": right_period},
            "period_comparability": comparability, "metrics": metrics, "dimensions": dimensions,
            "temporal": temporal, "quality": quality, "insights": insights}
