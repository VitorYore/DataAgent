"""Decisões explícitas sobre os candidatos já detectados nesta análise."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json


def preparar_revisao(report, analysis_id, dataframe=None):
    result = deepcopy(report)
    positions = {}
    result.setdefault("candidates", [])
    result.setdefault("total_candidates", 0)
    result.setdefault("possible_duplicate_entities", {})
    result.setdefault("decisions", [])
    for candidate in result.get("candidates", []):
        column = candidate["column"]
        left, right = candidate["left"], candidate["right"]
        key = [analysis_id, candidate["entity_type"], column, sorted([left["value"], right["value"]])]
        candidate.setdefault("candidate_id", sha256(json.dumps(key, ensure_ascii=False).encode("utf-8")).hexdigest()[:24])
        if dataframe is not None and column not in positions:
            positions[column] = {value: index for index, value in enumerate(dataframe[column].drop_duplicates())}
        order = positions.get(column, {left["value"]: 0, right["value"]: 1})
        recommended = min([left, right], key=lambda side: (-side["records"], order.get(side["value"], 0)))
        candidate.setdefault("recommended_value", recommended["value"])
        candidate.setdefault("status", "pending")
    return atualizar_contadores(result)


def atualizar_contadores(report):
    counts = {}
    for kind, total in report.get("possible_duplicate_entities", {}).items():
        counts[kind] = {"total": total, "pending": total, "merged": 0, "kept_separate": 0}
    for candidate in report.get("candidates", []):
        kind, status = candidate["entity_type"], candidate.get("status", "pending")
        if status != "pending":
            counts[kind]["pending"] -= 1
            counts[kind][status] += 1
    report["summary"] = counts
    return report


def validar_decisao(report, payload):
    if not isinstance(payload, dict) or set(payload) - {"candidate_id", "decision", "canonical_value"}:
        raise ValueError("Informe somente candidato, decisão e, opcionalmente, o label recomendado.")
    if payload.get("decision") not in ("merge", "keep_separate"):
        raise ValueError("Decisão inválida. Escolha unir ou manter separadas.")
    candidate = next((c for c in report.get("candidates", []) if c.get("candidate_id") == payload.get("candidate_id")), None)
    if candidate is None:
        raise ValueError("O candidato não pertence a esta análise.")
    if "canonical_value" in payload and payload["canonical_value"] != candidate["recommended_value"]:
        raise ValueError("O label deve ser a variante recomendada deste candidato.")
    expected = "merged" if payload["decision"] == "merge" else "kept_separate"
    if candidate["status"] not in ("pending", expected):
        raise ValueError("Alterar uma decisão confirmada ainda não é suportado.")
    if candidate["status"] == "pending" and expected == "merged":
        values = {candidate["left"]["value"], candidate["right"]["value"]}
        for other in report["candidates"]:
            if other["column"] == candidate["column"] and other["status"] == "merged":
                if values & {other["left"]["value"], other["right"]["value"]}:
                    raise ValueError("Uma variante já participa de outra união. Uniões sobrepostas não são suportadas nesta etapa.")
    return candidate


def registrar_decisao(dataframe, report, payload):
    candidate = validar_decisao(report, payload)
    if candidate["status"] != "pending":
        return report
    column = candidate["column"]
    if column not in dataframe or candidate["entity_type"] in report.get("stable_id_types", []):
        raise ValueError("A coluna não está disponível para resolução textual.")
    values = set(dataframe[column].dropna())
    if not {candidate["left"]["value"], candidate["right"]["value"]} <= values:
        raise ValueError("As variantes não estão presentes nos dados desta análise.")
    result = deepcopy(report)
    selected = next(c for c in result["candidates"] if c["candidate_id"] == candidate["candidate_id"])
    selected["status"] = "merged" if payload["decision"] == "merge" else "kept_separate"
    canonical = selected["recommended_value"] if payload["decision"] == "merge" else None
    selected["canonical_value"] = canonical
    result["decisions"].append({
        "candidate_id": selected["candidate_id"], "entity_type": selected["entity_type"],
        "column": column, "left": selected["left"]["value"], "right": selected["right"]["value"],
        "decision": payload["decision"], "canonical_value": canonical,
        "created_at": datetime.now(timezone.utc).isoformat(), "origin": "user_confirmation",
    })
    return atualizar_contadores(result)


def aplicar_aliases(dataframe, report):
    result = dataframe.copy()
    aliases = {}
    for candidate in report.get("candidates", []):
        if candidate.get("status") == "merged":
            column = candidate["column"]
            replacements = aliases.setdefault(column, {})
            replacements[candidate["left"]["value"]] = candidate["canonical_value"]
            replacements[candidate["right"]["value"]] = candidate["canonical_value"]
    for column, replacements in aliases.items():
        result[column] = result[column].replace(replacements)
    return result
