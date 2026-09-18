"""Conservatively flags isolated dates outside a well-supported dominant year interval."""
import pandas as pd


def analisar_anomalias_temporais(df: pd.DataFrame, coluna_data: str | None) -> dict:
    if not coluna_data or coluna_data not in df.columns:
        return {"mask": pd.Series(True, index=df.index), "confianca": 0.0, "quantidade": 0}

    dates = df[coluna_data]
    if not pd.api.types.is_datetime64_any_dtype(dates):
        dates = pd.to_datetime(dates, errors="coerce", format="mixed", dayfirst=True)
    valid = dates.dropna()
    all_true = pd.Series(True, index=df.index)
    if len(valid) < 50:
        return {"mask": all_true, "confianca": 0.0, "quantidade": 0}

    year_counts = valid.dt.year.value_counts().sort_index()
    years = list(year_counts.index)
    counts = [int(year_counts.loc[year]) for year in years]

    # Find the narrowest contiguous calendar-year interval containing >=95% of valid rows.
    required = int(len(valid) * 0.95 + 0.999999)
    best = None
    for left in range(len(years)):
        total = 0
        for right in range(left, len(years)):
            if right > left and years[right] != years[right - 1] + 1:
                break
            total += counts[right]
            if total >= required:
                candidate = (right - left, total, left, right)
                if best is None or candidate < best:
                    best = candidate
                break

    if best is None:
        return {
            "mask": all_true, "confianca": 0.0, "quantidade": 0,
            "periodo_predominante": None, "datas_exemplos": [],
        }

    _, inlier_count, left, right = best
    start_year, end_year = years[left], years[right]
    outlier_years = [
        year for year in years
        if year < start_year or year > end_year
    ]
    outlier_count = int(sum(year_counts.loc[year] for year in outlier_years))
    share = inlier_count / len(valid)
    sparse_limit = max(3, int(len(valid) * 0.01))
    strong = (
        share >= 0.95
        and outlier_count > 0
        and outlier_count / len(valid) <= 0.05
        and all(int(year_counts.loc[year]) <= sparse_limit for year in outlier_years)
        and end_year > start_year
    )
    if not strong:
        return {
            "mask": all_true, "confianca": round(share, 4), "quantidade": 0,
            "periodo_predominante": {
                "inicio": valid[valid.dt.year.between(start_year, end_year)].min().date().isoformat(),
                "fim": valid[valid.dt.year.between(start_year, end_year)].max().date().isoformat(),
            },
            "datas_exemplos": [],
        }

    anomalous = dates.notna() & (dates.dt.year.isin(outlier_years))
    mask = ~anomalous
    ordered_examples = dates[anomalous].drop_duplicates().sort_values()
    examples = pd.concat([ordered_examples.head(3), ordered_examples.tail(2)]).drop_duplicates()
    return {
        "mask": mask,
        "confianca": round(share, 4),
        "quantidade": int(anomalous.sum()),
        "periodo_predominante": {
            "inicio": valid[valid.dt.year.between(start_year, end_year)].min().date().isoformat(),
            "fim": valid[valid.dt.year.between(start_year, end_year)].max().date().isoformat(),
            "ano_inicio": int(start_year),
            "ano_fim": int(end_year),
        },
        "datas_exemplos": [value.date().isoformat() for value in examples],
        "anos_anomalos": [int(year) for year in outlier_years],
    }
