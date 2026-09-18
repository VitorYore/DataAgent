"""Índice rápido e arquivos completos por análise para o histórico V1.2."""
import json
from pathlib import Path

from src.history.analysis_history import listar_historico, ID_PATTERN

INDEX = "index.json"


def _atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def enriquecer_registro(summary, record):
    data = summary.get("dados") or {}
    temporal = summary.get("temporal") or {}
    points = temporal.get("serie_temporal") or []
    periods = sorted(str(p.get("periodo")) for p in points if isinstance(p, dict) and p.get("periodo"))
    metrics = summary.get("kpis") or {}
    record["analysis_id"] = record["id"]
    record["created_at"] = record.get("data_analise")
    record["mode"] = "multi" if len(record.get("arquivos") or []) > 1 else "single"
    record["analysis_status"] = "success"
    record["dataset"] = {"rows": data.get("quantidade_linhas"), "columns": data.get("quantidade_colunas")}
    record["period"] = {"start": periods[0] if periods else None, "end": periods[-1] if periods else None}
    record["available_metrics"] = [key for key, value in metrics.items() if isinstance(value, (int, float)) and not isinstance(value, bool)]
    dimensions = []
    customers, products = summary.get("clientes") or {}, summary.get("produtos") or {}
    if customers.get("quantidade_clientes") is not None or customers.get("ranking_valor_total") or customers.get("ranking_faturamento"):
        dimensions.append("cliente")
    if products.get("quantidade_produtos") is not None or products.get("ranking_produtos"):
        dimensions.append("produto")
    if summary.get("pagamentos") or summary.get("forma_pagamento"):
        dimensions.append("forma_pagamento")
    record["available_dimensions"] = dimensions
    record["quality"] = {key: data[key] for key in ("score_qualidade", "classificacao_qualidade", "total_valores_nulos", "linhas_duplicadas") if key in data}
    record["semantic_mapping_summary"] = data.get("mapeamento_semantico") or {}
    record["report_available"] = True
    return record


def persistir_resumo(summary, record, folder):
    folder = Path(folder)
    identifier = record.get("id")
    if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
        raise ValueError("Identificador de análise inválido.")
    _atomic(folder / "details" / f"{identifier}.json", summary)
    record = enriquecer_registro(summary, dict(record))
    _atomic(folder / f"{identifier}.json", record)
    index_path = folder / INDEX
    if index_path.exists():
        existing = json.loads(index_path.read_text(encoding="utf-8"))
        items = existing.get("items", []) if isinstance(existing, dict) else []
    else:
        items = listar_historico(folder)
    items = [item for item in items if item.get("id") != identifier]
    items.append(record)
    items.sort(key=lambda item: (item.get("created_at") or item.get("data_analise") or "", item.get("id", "")), reverse=True)
    _atomic(index_path, {"version": 1, "items": items})


def listar_indice(folder, limit=None, offset=0):
    folder = Path(folder)
    path = folder / INDEX
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("items"), list):
            raise ValueError("Índice do histórico inválido.")
        items = value["items"]
    else:
        items = listar_historico(folder)
    start = max(0, int(offset))
    return items[start:start + int(limit)] if limit is not None else items[start:]


def obter_resumo(identifier, folder):
    if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
        raise FileNotFoundError("Análise não encontrada.")
    folder = Path(folder).resolve()
    item_path = (folder / f"{identifier}.json").resolve()
    detail_path = (folder / "details" / f"{identifier}.json").resolve()
    if item_path.parent != folder or detail_path.parent != (folder / "details").resolve():
        raise FileNotFoundError("Análise não encontrada.")
    item = json.loads(item_path.read_text(encoding="utf-8"))
    if item.get("analysis_status") != "success":
        raise FileNotFoundError("Análise não encontrada.")
    summary = json.loads(detail_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError("Resumo histórico inválido.")
    return summary
