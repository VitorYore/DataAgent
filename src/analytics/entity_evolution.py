"""Agregados temporários da população completa; nunca usa rankings como entrada."""

import math

import pandas as pd

from src.analytics.business import encontrar_coluna_por_papel
from src.analytics.temporal_comparison import comparar_serie, comparar_valores, magnitude_referencia, numero_finito


COBERTURA_MINIMA = 0.95


def agregar_entidades_periodo(df, mapping, series, entity_report=None):
    """Recebe datas já tratadas e séries globais já calculadas na mesma população."""
    date = encontrar_coluna_por_papel(mapping, "data")
    if not date or not pd.api.types.is_datetime64_any_dtype(df[date]):
        return []
    columns = {metric: encontrar_coluna_por_papel(mapping, metric) for metric in series}
    columns = {metric: col for metric, col in columns.items() if col}
    if not columns:
        return []
    periods = df[date].dt.to_period("M").astype("string")
    merged = {(c["column"], c.get("canonical_value")) for c in (entity_report or {}).get("candidates", [])
              if c.get("status") == "merged"}
    results = []
    for kind in ("cliente", "produto"):
        id_col = encontrar_coluna_por_papel(mapping, kind + "_id")
        label_col = encontrar_coluna_por_papel(mapping, kind)
        identity_col = id_col or label_col
        if not identity_col:
            continue
        # Construir somente estas colunas evita propagar auditoria pesada nos attrs.
        data = pd.DataFrame({"period": periods.to_numpy(), "entity": df[identity_col].to_numpy()})
        blank = data["entity"].map(lambda v: isinstance(v, str) and not v.strip())
        if blank.any():
            data.loc[blank, "entity"] = None
        for metric, column in columns.items():
            values = pd.to_numeric(df[column], errors="coerce")
            data[metric] = values.where(values.notna() & values.ne(float("inf")) & values.ne(float("-inf"))).to_numpy()
        data = data.dropna(subset=["period"])
        groups = data.groupby(["period", "entity"], dropna=False, sort=False)
        sums = groups[list(columns)].sum(min_count=1)
        counts = groups[list(columns)].count()
        sizes = groups.size()
        labels = {}
        if id_col and label_col:
            for identity, label in df[[id_col, label_col]].dropna().drop_duplicates(id_col).itertuples(index=False, name=None):
                labels[identity] = str(label)
        for metric in columns:
            by_period = {}
            for ((period, identity), value), valid, records in zip(sums[metric].items(), counts[metric], sizes):
                valid, records = int(valid), int(records)
                bucket = by_period.setdefault(str(period), {"entities": {}, "records": 0, "valid": 0,
                                                          "identified_valid": 0, "sum": 0.0, "negative_groups": 0})
                bucket["records"] += records
                bucket["valid"] += valid
                number = numero_finito(value)
                if number is not None:
                    bucket["sum"] += number
                    bucket["negative_groups"] += int(number < 0)
                if pd.isna(identity):
                    continue
                bucket["identified_valid"] += valid
                source = "stable_id" if id_col else "confirmed_alias" if (identity_col, identity) in merged else "text"
                bucket["entities"][str(identity)] = {
                    "id": str(identity) if id_col else None, "value": str(identity),
                    "label": labels.get(identity, str(identity)), "identity_source": source,
                    "value_sum": number, "records": records, "valid": valid,
                }
            results.append({"entity_type": kind, "metric": metric, "periods": by_period,
                            "global_values": series[metric], "input_records": len(df),
                            "undated_records": int(periods.isna().sum())})
    return results


def comparar_entidades(aggregate):
    """Ausência permanece ausência; saldo global inclui também valores não atribuídos."""
    global_values = aggregate["global_values"]
    reference = magnitude_referencia(global_values.values())
    entity_series = {}
    for bucket in aggregate["periods"].values():
        for key, entity in bucket["entities"].items():
            entity_series.setdefault(key, []).append(entity["value_sum"])
    entity_references = {key: magnitude_referencia(values) for key, values in entity_series.items()}
    for global_comparison in comparar_serie(global_values):
        if not global_comparison["comparable"] or not global_comparison["continuous"]:
            continue
        before, after = global_comparison["previous_period"], global_comparison["current_period"]
        left, right = (aggregate["periods"].get(p) for p in (before, after))
        if not left or not right:
            continue
        coverage = {}
        for period, bucket in ((before, left), (after, right)):
            coverage[period] = {
                "records": bucket["records"], "valid_metric": bucket["valid"],
                "valid_identity_metric": bucket["identified_valid"],
                "population": len(bucket["entities"]),
                "input_records": aggregate["input_records"], "undated_records": aggregate["undated_records"],
                "reconciled": math.isclose(bucket["sum"], global_values[period], rel_tol=1e-9, abs_tol=1e-6),
            }
        if not all(c["reconciled"] for c in coverage.values()):
            continue
        complete = all(c["records"] > 0 and c["valid_identity_metric"] / c["records"] >= COBERTURA_MINIMA
                       for c in coverage.values())
        complete = complete and aggregate["undated_records"] / aggregate["input_records"] <= 1 - COBERTURA_MINIMA
        rows, absent = [], {"newly_observed": 0, "not_observed_current": 0, "missing_metric": 0}
        for key in sorted(left["entities"].keys() | right["entities"].keys()):
            a, b = left["entities"].get(key), right["entities"].get(key)
            if a is None or b is None:
                absent["newly_observed" if a is None else "not_observed_current"] += 1
                continue
            if a["value_sum"] is None or b["value_sum"] is None:
                absent["missing_metric"] += 1
                continue
            comparison = comparar_valores(a["value_sum"], b["value_sum"],
                reference_magnitude=entity_references[key], previous_period=before,
                current_period=after, require_consecutive=True)
            if not comparison["comparable"]:
                continue
            rows.append({"entity": {k: b[k] for k in ("id", "value", "label", "identity_source")},
                         "comparison": comparison, "records": {before: a["records"], after: b["records"]},
                         "valid": {before: a["valid"], after: b["valid"]},
                         "previous_share": a["value_sum"] / global_values[before] * 100
                         if global_values[before] > 0 and not left["negative_groups"] else None,
                         "current_share": b["value_sum"] / global_values[after] * 100
                         if global_values[after] > 0 and not right["negative_groups"] else None})
        decline = -sum(min(0, r["comparison"]["absolute_change"]) for r in rows)
        growth = sum(max(0, r["comparison"]["absolute_change"]) for r in rows)
        yield {"entity_type": aggregate["entity_type"], "metric": aggregate["metric"],
               "global_comparison": global_comparison, "reference": reference,
               "coverage": coverage, "complete_fields": complete, "rows": rows,
               "absences": absent, "gross_negative_change_matched": decline,
               "gross_positive_change_matched": growth,
               "unexplained_by_matched_pairs": global_comparison["absolute_change"] - (growth - decline)}
