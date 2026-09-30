"""Comparações numéricas e continuidade, sem preencher períodos ausentes."""

import math
import re


LIMIAR_BASE_RELATIVA = 0.05


def numero_finito(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def magnitude_referencia(values):
    magnitudes = []
    for value in values:
        number = numero_finito(value)
        if number is not None and number != 0:
            magnitudes.append(abs(number))
    if not magnitudes:
        return 0.0
    magnitudes.sort()
    middle = len(magnitudes) // 2
    return magnitudes[middle] if len(magnitudes) % 2 else magnitudes[middle - 1] / 2 + magnitudes[middle] / 2


def ordinal_periodo(period, granularity="M"):
    text = str(period)
    if text[:4] == "0000":
        return None
    if granularity == "M" and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", text):
        year, month = map(int, text.split("-"))
        return year * 12 + month - 1
    if granularity == "Q" and re.fullmatch(r"\d{4}Q[1-4]", text):
        return int(text[:4]) * 4 + int(text[-1]) - 1
    if granularity in ("Y", "A") and re.fullmatch(r"\d{4}", text):
        return int(text)
    return None


def comparar_valores(previous_value, current_value, *, reference_magnitude=None,
                     previous_period=None, current_period=None, granularity="M",
                     require_consecutive=False):
    previous, current = numero_finito(previous_value), numero_finito(current_value)
    result = {
        "previous_value": previous, "current_value": current,
        "previous_period": str(previous_period) if previous_period is not None else None,
        "current_period": str(current_period) if current_period is not None else None,
        "absolute_change": None, "percentage_change": None, "direction": None,
        "percentage_valid": False, "comparable": False, "reason": None,
        "continuous": None, "granularity": granularity,
        "reference_magnitude": None,
    }
    if previous is None or current is None or not math.isfinite(current - previous):
        result["reason"] = "invalid_value"
        return result
    delta = current - previous
    result.update(absolute_change=delta, direction="increase" if delta > 0 else "decrease" if delta < 0 else "stable")
    if previous_period is not None or current_period is not None:
        before = ordinal_periodo(previous_period, granularity)
        after = ordinal_periodo(current_period, granularity)
        if before is None or after is None or after <= before:
            result["reason"] = "invalid_period"
            return result
        result["continuous"] = after == before + 1
        if require_consecutive and not result["continuous"]:
            result["reason"] = "non_consecutive_periods"
            return result
    result["comparable"] = True
    # A referência local também protege um salto isolado numa série de valores pequenos.
    reference = max(magnitude_referencia([previous, current]), numero_finito(reference_magnitude) or 0)
    result["reference_magnitude"] = reference
    if previous == 0:
        result["reason"] = "zero_reference"
    elif previous < 0:
        result["reason"] = "negative_reference"
    elif current < 0:
        result["reason"] = "sign_change"
    elif previous < reference * LIMIAR_BASE_RELATIVA:
        result["reason"] = "low_reference_base"
    else:
        percentage = delta / previous * 100
        if math.isfinite(percentage):
            result.update(percentage_change=round(percentage, 2), percentage_valid=True)
        else:
            result["reason"] = "invalid_percentage"
    return result


def comparar_serie(values, granularity="M"):
    """Recebe uma série já agregada. Meses nulos/quebrados não viram zero."""
    periods = sorted(values, key=lambda p: (ordinal_periodo(p, granularity) is None,
                                          ordinal_periodo(p, granularity) or 0, str(p)))
    reference = magnitude_referencia(values.values())
    return [comparar_valores(values[before], values[after], reference_magnitude=reference,
                            previous_period=before, current_period=after,
                            granularity=granularity, require_consecutive=True)
            for before, after in zip(periods, periods[1:])]
