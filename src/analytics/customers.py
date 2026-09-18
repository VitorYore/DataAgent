import pandas as pd

from src.analytics.column_mapper import mapear_colunas
from src.analytics.business import encontrar_coluna_por_papel
from src.analytics.entity_helpers import preparar_entidade, formatar_entidade


METRICAS_CLIENTE = (
    ("faturamento", "Faturamento"),
    ("valor_total", "Valor Total"),
    ("valor_com_desconto", "Valor com Desconto"),
    ("margem_bruta", "Margem Bruta"),
    ("lucro", "Lucro"),
)


def _agregar_metrica(df, grupo, coluna):
    if not coluna:
        return pd.Series(dtype=float)
    return df.dropna(subset=[grupo]).groupby(grupo)[coluna].sum(min_count=1).dropna().sort_values(ascending=False)


def _ranking(valores, mapa_rotulos, possui_id, conceito):
    return [
        {"posicao": pos, "cliente": formatar_entidade(cliente, mapa_rotulos),
         "cliente_id": str(cliente) if possui_id else None, "valor": round(float(valor), 2),
         "conceito": conceito}
        for pos, (cliente, valor) in enumerate(valores.head(10).items(), start=1)
    ]


def analisar_clientes(df: pd.DataFrame) -> dict:
    mapping = mapear_colunas(df)
    id_col = encontrar_coluna_por_papel(mapping, "cliente_id")
    name_col = encontrar_coluna_por_papel(mapping, "cliente")
    group_col, labels_by_id = preparar_entidade(df, id_col, name_col)
    if not group_col:
        return {"erro": "Não foi possível identificar uma coluna de clientes."}

    columns = {concept: encontrar_coluna_por_papel(mapping, concept) for concept, _ in METRICAS_CLIENTE}
    labels = dict(METRICAS_CLIENTE)
    values = {concept: _agregar_metrica(df, group_col, column) for concept, column in columns.items()}
    # Participation/concentration use business-volume concepts, not profit or margin.
    primary = next(
        (concept for concept in ("faturamento", "valor_total", "valor_com_desconto")
         if not values[concept].empty),
        None,
    )
    result = {
        "quantidade_clientes": int(df[group_col].dropna().nunique()),
        "coluna_cliente": name_col or id_col, "coluna_cliente_id": id_col,
        "metrica_principal": ({"conceito": primary, "label": labels[primary], "coluna": columns[primary]} if primary else None),
        "rankings": {}, "participacao_maior_cliente": None,
        "participacao_maior_cliente_metrica": None, "concentracao_top_5": None,
        "concentracao_top_5_metrica": None, "clientes_resultado_negativo": None,
        "clientes_metrica_negativa": None, "ranking_faturamento": [], "ranking_lucro": [],
        "insights_clientes": [],
    }

    for concept, label in METRICAS_CLIENTE:
        ordered = values[concept]
        if ordered.empty:
            continue
        ranked = _ranking(ordered, labels_by_id, bool(id_col), concept)
        result["rankings"][concept] = {"conceito": concept, "label": label, "items": ranked}
        leader_id = ordered.index[0]
        leader = {"cliente": formatar_entidade(leader_id, labels_by_id),
                  "cliente_id": str(leader_id) if id_col else None,
                  "valor": round(float(ordered.iloc[0]), 2), "conceito": concept, "label": label}
        result[f"maior_{concept}"] = leader
        if concept == "faturamento":
            result["maior_faturamento"] = {**leader, "faturamento": leader["valor"]}
            result["top_5_faturamento"] = [
                {"cliente": formatar_entidade(k, labels_by_id), "cliente_id": str(k), "faturamento": round(float(v), 2)}
                for k, v in ordered.head(5).items()
            ]
            profit_by_id = {str(key): value for key, value in values["lucro"].items()}
            result["ranking_faturamento"] = [
                {
                    "posicao": item["posicao"], "cliente": item["cliente"],
                    "cliente_id": item["cliente_id"], "faturamento": item["valor"],
                    "lucro": round(float(profit_by_id[item["cliente_id"]]), 2)
                    if item["cliente_id"] in profit_by_id else None,
                }
                for item in ranked
            ]
        elif concept == "valor_total":
            result["maior_valor_total"] = {**leader, "valor_total": leader["valor"]}
            result["ranking_valor_total"] = [{**item, "valor_total": item["valor"]} for item in ranked]
        elif concept == "valor_com_desconto":
            result["maior_valor_com_desconto"] = {**leader, "valor_com_desconto": leader["valor"]}
        elif concept == "margem_bruta":
            result["maior_margem_bruta"] = {**leader, "margem_bruta": leader["valor"]}
            negative = ordered[ordered < 0]
            result["clientes_margem_bruta_negativa"] = int(len(negative))
            result["clientes_com_margem_bruta_negativa"] = [
                {"cliente": formatar_entidade(k, labels_by_id), "cliente_id": str(k), "margem_bruta": round(float(v), 2)}
                for k, v in negative.items()
            ]
            result["clientes_metrica_negativa"] = {"conceito": concept, "label": label, "quantidade": int(len(negative))}
        elif concept == "lucro":
            result["maior_lucro"] = {**leader, "lucro": leader["valor"]}
            negative = ordered[ordered < 0]
            result["clientes_resultado_negativo"] = int(len(negative))
            result["clientes_metrica_negativa"] = {"conceito": concept, "label": label, "quantidade": int(len(negative))}
            result["clientes_com_prejuizo"] = [
                {"cliente": formatar_entidade(k, labels_by_id), "cliente_id": str(k), "lucro": round(float(v), 2)}
                for k, v in negative.items()
            ]
            revenue_by_id = {str(key): value for key, value in values["faturamento"].items()}
            result["ranking_lucro"] = [
                {
                    "posicao": item["posicao"], "cliente": item["cliente"],
                    "cliente_id": item["cliente_id"], "lucro": item["valor"],
                    "faturamento": round(float(revenue_by_id[item["cliente_id"]]), 2)
                    if item["cliente_id"] in revenue_by_id else None,
                }
                for item in ranked
            ]

    if primary:
        total = df[columns[primary]].sum(min_count=1)
        if pd.notna(total) and total != 0:
            metadata = {"conceito": primary, "label": labels[primary]}
            result["participacao_maior_cliente_metrica"] = metadata
            result["concentracao_top_5_metrica"] = metadata
            result["participacao_maior_cliente"] = round(float(values[primary].iloc[0] / total * 100), 2)
            result["concentracao_top_5"] = round(float(values[primary].head(5).sum() / total * 100), 2)

    if primary and result["participacao_maior_cliente"] is not None:
        top5 = f"{result['concentracao_top_5']:.2f}".replace(".", ",")
        share = f"{result['participacao_maior_cliente']:.2f}".replace(".", ",")
        result["insights_clientes"].extend([
            f"Os cinco maiores clientes representam {top5}% de {labels[primary]}.",
            f"O maior cliente representa {share}% de {labels[primary]}.",
        ])
    if not values["faturamento"].empty and not values["lucro"].empty:
        if values["faturamento"].index[0] != values["lucro"].index[0]:
            result["insights_clientes"].append(
                "O cliente com maior faturamento difere do cliente com maior lucro."
            )
    negative_metric = result.get("clientes_metrica_negativa")
    if negative_metric and negative_metric["quantidade"]:
        adjetivo = "negativa" if negative_metric["conceito"] == "margem_bruta" else "negativo"
        quantidade = negative_metric["quantidade"]
        sujeito = "cliente apresenta" if quantidade == 1 else "clientes apresentam"
        result["insights_clientes"].append(
            f"{quantidade} {sujeito} {negative_metric['label']} {adjetivo}."
        )
    return result
