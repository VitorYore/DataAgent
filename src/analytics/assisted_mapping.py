"""Perfis estruturais e validação simples para mapeamento semântico assistido."""
import pandas as pd

from src.analytics.column_mapper import REGRAS, conceito_por_rotulo_cabecalho, mapear_colunas


class SemanticMappingRequired(ValueError):
    def __init__(self, dataframe, detected_columns, required_mappings, automatic_mappings, analysis_files=None):
        super().__init__("Confirmação semântica necessária.")
        self.dataframe = dataframe
        self.detected_columns = detected_columns
        self.required_mappings = required_mappings
        self.automatic_mappings = automatic_mappings
        self.analysis_files = analysis_files or []


CONCEITOS_EXTRAS = {
    "forma_pagamento": {"label": "Forma de pagamento", "tipo": "dimensao"},
    "identificador": {"label": "Identificador", "tipo": "identificador"},
    "outro": {"label": "Outro / dimensão genérica", "tipo": "qualquer"},
    "ignorar": {"label": "Ignorar", "tipo": "qualquer"},
}
CONCEITOS = {
    key: {
        "label": key.replace("_", " ").capitalize(),
        "tipo": regra["tipo"],
    }
    for key, regra in REGRAS.items()
}
CONCEITOS.update(CONCEITOS_EXTRAS)
ROTULOS = {
    "faturamento": "Faturamento", "custo": "Custo", "lucro": "Lucro",
    "margem_lucro": "Margem de lucro", "quantidade": "Quantidade",
    "preco_unitario": "Preço unitário", "custo_unitario": "Custo unitário",
    "cliente": "Cliente", "produto": "Produto", "pedido": "Pedido",
    "pagamento": "Forma de pagamento", "forma_pagamento": "Forma de pagamento",
    "identificador": "Identificador provável", "outro": "Outro / dimensão genérica",
    "ignorar": "Ignorar", "data": "Data", "descricao": "Descrição",
}
for conceito, label in ROTULOS.items():
    if conceito in CONCEITOS:
        CONCEITOS[conceito]["label"] = label

ALIAS_COLUNAS = {
    "data": "Data", "identificador": "Identificador", "pedido": "Pedido",
    "valor_total": "Valor_Total", "valor_com_desconto": "Valor_Com_Desconto",
    "margem_bruta": "Margem_Bruta", "margem_bruta_percentual": "Margem_Bruta_Percentual",
    "venda_id": "Venda_ID", "faturamento": "Faturamento",
    "custo": "Custo_Total", "custo_unitario": "Custo_Unitario",
    "lucro": "Lucro", "margem_lucro": "Margem_Lucro",
    "quantidade": "Quantidade", "preco_unitario": "Preco_Unitario",
    "cliente": "Cliente", "cliente_id": "Cliente_ID", "produto": "Produto",
    "produto_id": "Produto_ID", "forma_pagamento": "Forma_Pagamento",
    "pagamento": "Pagamento", "status": "Status", "desconto": "Desconto",
    "categoria": "Categoria", "descricao": "Descricao", "loja": "Loja",
    "loja_id": "Loja_ID", "colaborador": "Colaborador", "canal_venda": "Canal_Venda",
    "estoque_atual": "Estoque_Atual", "taxa_devolucao": "Taxa_Devolucao",
}

NUMERICOS = {"faturamento", "custo", "custo_unitario", "lucro", "margem_lucro", "valor_total", "valor_com_desconto", "margem_bruta", "margem_bruta_percentual", "quantidade",
             "preco_unitario", "desconto", "estoque_atual", "estoque_minimo", "estoque_maximo",
             "taxa_devolucao", "quantidade_devolvida", "numero_devolucoes", "avaliacao_media"}
DIMENSOES = {k for k, v in CONCEITOS.items() if v["tipo"] in ("dimensao", "identificador_dimensao")}
PAGAMENTOS = {"dinheiro", "credito", "debito", "pix", "cheque", "transferencia", "transferencia bancaria"}


def _type(series: pd.Series) -> tuple[str, float]:
    values = series.dropna()
    if values.empty:
        return "vazio", 0.0
    if pd.api.types.is_datetime64_any_dtype(values):
        return "data", 1.0
    parsed_dates = pd.to_datetime(values.astype(str), errors="coerce", format="mixed", dayfirst=True)
    date_ratio = float(parsed_dates.notna().mean())
    if date_ratio >= 0.95:
        return "data", date_ratio
    numbers = pd.to_numeric(values, errors="coerce")
    numeric_ratio = float(numbers.notna().mean())
    if numeric_ratio >= 0.95:
        cardinality = numbers.nunique(dropna=True)
        unique_ratio = cardinality / max(1, len(numbers))
        integers = bool((numbers % 1 == 0).all())
        differences = numbers.diff().dropna().abs()
        sequence_ratio = float((differences == 1).mean()) if not differences.empty else 0.0
        role = "identificador_provavel" if unique_ratio >= 0.95 and integers and sequence_ratio >= 0.35 else (
            "valor_monetario" if bool((numbers % 1 != 0).any()) else "valor_numerico"
        )
        return role, numeric_ratio
    text = values.astype(str).str.strip().str.casefold()
    payment_ratio = float(text.map(lambda value: any(value == candidate or value.startswith(candidate + " ") for candidate in PAGAMENTOS)).mean())
    if payment_ratio >= 0.8:
        return "categoria_pagamento", payment_ratio
    return "texto", max(0.0, 1.0 - numeric_ratio)


def _compatible(role: str) -> list[str]:
    if role == "data":
        return ["data", "ignorar"]
    if role in {"valor_numerico", "valor_monetario"}:
        return [c for c in ("faturamento", "custo", "lucro", "valor_total", "valor_com_desconto",
                             "margem_bruta", "margem_bruta_percentual", "quantidade", "preco_unitario",
                             "custo_unitario", "desconto", "margem_lucro", "estoque_atual",
                             "taxa_devolucao", "outro", "ignorar") if c in CONCEITOS]
    if role == "identificador_provavel":
        return [c for c in ("identificador", "pedido", "venda_id", "cliente_id", "produto_id",
                             "loja_id", "colaborador_id", "outro", "ignorar") if c in CONCEITOS]
    if role == "categoria_pagamento":
        return [c for c in ("forma_pagamento", "pagamento", "status", "categoria", "outro", "ignorar") if c in CONCEITOS]
    if role == "texto":
        return [c for c in ("cliente", "produto", "categoria", "descricao", "status", "pagamento", "forma_pagamento",
                             "loja", "colaborador", "canal_venda", "regiao", "cidade", "outro", "ignorar") if c in CONCEITOS]
    return ["ignorar"]


def _id_positions(df: pd.DataFrame) -> set[int]:
    ingestion = df.attrs.get("ingestao", {})
    structures = [ingestion] if isinstance(ingestion, dict) else []
    structures += [value for value in ingestion.values() if isinstance(value, dict)] if isinstance(ingestion, dict) else []
    positions = set()
    for structure in structures:
        normalization = structure.get("normalizacao", {})
        for position in normalization.get("posicoes_identificadores_provaveis", []):
            if isinstance(position, int) and position > 0:
                positions.add(position - 1)
    return positions


def _evidencias_cabecalhos(df: pd.DataFrame) -> dict:
    ingestao = df.attrs.get("ingestao", {})
    structures = [ingestao] if isinstance(ingestao, dict) else []
    if isinstance(ingestao, dict):
        structures.extend(value for value in ingestao.values() if isinstance(value, dict))
    result = {}
    for structure in structures:
        normalizacao = structure.get("normalizacao", {})
        for header in normalizacao.get("evidencias_cabecalho_tardio", []):
            labels = [item.get("rotulo") for item in header.get("colunas", [])]
            for item in header.get("colunas", []):
                column = f"coluna_{item.get('posicao')}"
                if column in df.columns:
                    result[column] = {**item, "origem": header.get("origem"), "validado": header.get("validado"), "rotulos_contexto": labels}
    return result


def perfilar_colunas(df: pd.DataFrame) -> tuple[list[dict], list[dict], dict]:
    automatic = mapear_colunas(df)
    detected, required, automatic_mappings = [], [], {}
    id_positions = _id_positions(df)
    header_evidence = _evidencias_cabecalhos(df)
    minimum_values = max(3, int(len(df) * 0.02))
    for position, name in enumerate(df.columns):
        series = df[name]
        role, structural_confidence = _type(series)
        if position in id_positions and series.notna().sum() >= max(20, int(len(df) * 0.7)):
            role, structural_confidence = "identificador_provavel", float(series.notna().mean())
        mapped = automatic.get(name, {})
        semantic = mapped.get("papel") if mapped.get("confianca", 0) >= 80 else None
        confidence = round(float(mapped.get("confianca", 0)) / 100, 2)
        evidence = header_evidence.get(str(name))
        suggestion = None
        mapping_origin = "nome_coluna" if semantic else None
        if evidence:
            suggestion = conceito_por_rotulo_cabecalho(evidence.get("rotulo", ""), evidence.get("rotulos_contexto"))
            evidence_confidence = float(evidence.get("confianca", 0)) / 100
            role_compatible = suggestion in _compatible(role) or (role == "vazio" and suggestion == "margem_bruta_percentual")
            if evidence.get("validado") and evidence.get("mapeamento_permitido") and suggestion and role_compatible:
                if evidence_confidence >= 0.95:
                    semantic, confidence, mapping_origin = suggestion, evidence_confidence, evidence.get("origem")
            elif suggestion:
                mapping_origin = evidence.get("origem")
        if semantic is None and role == "data" and structural_confidence >= 0.95:
            semantic, confidence = "data", structural_confidence
        if semantic is None and role == "categoria_pagamento" and structural_confidence >= 0.8:
            semantic, confidence = "forma_pagamento", structural_confidence
        if semantic is None and role == "identificador_provavel":
            semantic, confidence = "identificador", structural_confidence
        state = "provavel" if semantic == "identificador" or role == "categoria_pagamento" else "confirmado" if semantic else "desconhecido"
        examples = []
        values = series.dropna().drop_duplicates()
        if role == "identificador_provavel":
            examples = ["Identificadores preservados", "Valores ocultados por privacidade"]
        elif role in {"valor_monetario", "valor_numerico"}:
            numeric_examples = pd.to_numeric(series, errors="coerce").dropna().drop_duplicates().head(3)
            examples = [str(value)[:80] for value in numeric_examples.tolist()]
        elif role == "texto" and values.nunique() > 30:
            examples = ["Exemplo textual ocultado", "Valores com alta cardinalidade", "Conteúdo preservado"]
        else:
            examples = [str(value)[:80] for value in values.head(3).tolist()]
        compatible = _compatible(role)
        if semantic and semantic != "identificador" or semantic == "identificador" and mapping_origin in {"cabecalho_posterior", "cabecalho_repetido"}:
            automatic_mappings[str(name)] = semantic
        profile = {
            "nome": str(name),
            "papel_estrutural": role,
            "confianca_estrutural": round(structural_confidence, 2),
            "conceito_semantico": semantic,
            "confianca_semantica": confidence,
            "estado": state,
            "exemplos": examples,
            "percentual_nulos": round(float(series.isna().mean() * 100), 2),
            "cardinalidade": int(series.nunique(dropna=True)),
            "mapeamento_relevante": int(series.notna().sum()) >= minimum_values,
            "conceitos_compativeis": compatible,
            "sugestao_semantica": suggestion,
            "origem_mapeamento": mapping_origin,
            "confianca_mapeamento": confidence if semantic else (round(float(evidence.get("confianca", 0)) / 100, 2) if evidence else None),
        }
        detected.append(profile)
        # Somente estruturas normalizadas com conceitos de negócio ainda ambíguos
        # pedem confirmação. Tabelas convencionais preservam o fluxo existente.
        if profile["mapeamento_relevante"] and (not semantic or (role == "identificador_provavel" and semantic == "identificador")) and role in {"valor_numerico", "valor_monetario", "identificador_provavel", "categoria_pagamento", "texto"} and compatible != ["ignorar"]:
            required.append({"coluna": str(name), "conceitos_compativeis": compatible})
    return detected, required, automatic_mappings


def precisa_mapeamento(df: pd.DataFrame) -> tuple[bool, list[dict], list[dict], dict]:
    ingestao = df.attrs.get("ingestao", {})
    normalizado = isinstance(ingestao, dict) and (
        bool(ingestao.get("normalizacao")) or any(bool(item.get("normalizacao")) for item in ingestao.values() if isinstance(item, dict))
    )
    detected, required, automatic = perfilar_colunas(df)
    mapper = mapear_colunas(df)
    business_mapped = any(
        item.get("papel") in {"faturamento", "custo", "lucro", "valor_total", "valor_com_desconto", "margem_bruta", "quantidade", "preco_unitario"}
        and item.get("confianca", 0) >= 80 for item in mapper.values()
    ) or any(concept in {"faturamento", "custo", "lucro", "valor_total", "valor_com_desconto", "margem_bruta", "quantidade", "preco_unitario"}
             for concept in automatic.values())
    required_names = {item["coluna"] for item in required}
    suggested_ambiguous = any(
        item["nome"] in required_names
        and item.get("sugestao_semantica")
        and not item.get("conceito_semantico")
        for item in detected
    )
    ask = normalizado and bool(required) and (not business_mapped or suggested_ambiguous)
    return ask, detected, required, automatic


def validar_mapeamentos(df: pd.DataFrame, mappings: dict) -> dict:
    if not isinstance(mappings, dict) or not mappings:
        raise ValueError("Informe ao menos um mapeamento.")
    _, required, _ = perfilar_colunas(df)
    candidates = {item["coluna"]: item["conceitos_compativeis"] for item in required}
    missing = sorted(set(candidates) - set(mappings))
    extra = sorted(set(mappings) - set(df.columns))
    if missing:
        raise ValueError(f"Defina um significado ou selecione Ignorar para: {', '.join(missing)}.")
    if extra:
        raise ValueError(f"Colunas inexistentes: {', '.join(extra)}.")
    chosen, used = {}, set()
    for column, concept in mappings.items():
        if not isinstance(concept, str) or concept not in CONCEITOS:
            raise ValueError(f"Conceito não permitido para {column}.")
        if column not in candidates or concept not in candidates[column]:
            raise ValueError(f"O conceito {concept} é incompatível com a coluna {column}.")
        if concept not in {"outro", "ignorar", "identificador"} and concept in used:
            raise ValueError(f"Mapeamento conflitante: o conceito {concept} foi selecionado mais de uma vez.")
        if concept not in {"outro", "ignorar", "identificador"}:
            used.add(concept)
        chosen[column] = concept
    return chosen


def aplicar_mapeamentos(df: pd.DataFrame, mappings: dict) -> tuple[pd.DataFrame, list[dict]]:
    result = df.copy()
    audit = []
    rename = {}
    drop = []
    generic = 1
    date_columns = []
    for column, concept in mappings.items():
        if concept == "ignorar":
            drop.append(column)
            audit.append({"tipo": "mapeamento_semantico_usuario", "coluna": column, "conceito": concept,
                          "descricao": "Coluna excluída somente do dataset analítico por confirmação do usuário."})
        else:
            if concept == "data":
                date_columns.append(column)
            target = ALIAS_COLUNAS.get(concept, concept.title().replace("_", "_"))
            if concept == "outro":
                target = f"Dimensao_Generica_{generic}"
                generic += 1
            elif concept == "identificador":
                target = f"Identificador_{generic}"
                generic += 1
            if target:
                rename[column] = target
            audit.append({"tipo": "mapeamento_semantico_usuario", "coluna": column, "conceito": concept,
                          "descricao": f"Mapeamento confirmado pelo usuário: {column} → {concept}."})
    result = result.drop(columns=drop).rename(columns=rename)
    for column in date_columns:
        converted = pd.to_datetime(result[rename.get(column, column)], errors="coerce", format="mixed", dayfirst=True)
        confidence = float(converted.notna().sum() / max(1, result[rename.get(column, column)].notna().sum()))
        if confidence < 0.95:
            raise ValueError(f"A coluna {column} não possui confiança suficiente para ser tratada como data.")
        invalid = int(result[rename.get(column, column)].notna().sum() - converted.notna().sum())
        result[rename.get(column, column)] = converted
        if invalid:
            audit.append({"tipo": "conversao_data_com_valores_invalidos", "coluna": column, "conceito": "data",
                          "descricao": f"Conversão de data com alta confiança; {invalid} valores não parseáveis ficaram nulos no dataset analítico. O arquivo enviado permanece preservado."})
    result.attrs.update(df.attrs)
    result.attrs["mapeamento_semantico_usuario"] = audit
    result.attrs["mapeamentos_confirmados"] = dict(mappings)
    return result, audit


def aplicar_mapeamento_completo(df: pd.DataFrame, automatic: dict, confirmed: dict) -> tuple[pd.DataFrame, list[dict]]:
    combined = {**(automatic or {}), **(confirmed or {})}
    # Perfis automáticos só incluem campos que já foram considerados seguros.
    for column, concept in combined.items():
        if concept not in CONCEITOS or column not in df.columns:
            raise ValueError("Mapeamento automático ou confirmado inválido.")
    if confirmed:
        validar_mapeamentos(df, confirmed)
    result, audit = aplicar_mapeamentos(df, combined)
    automatic_only = set(automatic or {}) - set(confirmed or {})
    for item in audit:
        if item["coluna"] in automatic_only and item["tipo"] == "mapeamento_semantico_usuario":
            item["tipo"] = "mapeamento_semantico_automatico"
            item["descricao"] = f"Conceito identificado automaticamente: {item['conceito']}."
    result.attrs["mapeamentos_confirmados"] = dict(confirmed or {})
    result.attrs["mapeamentos_automaticos"] = dict(automatic or {})
    return result, audit


def conceitos_publicos() -> list[dict]:
    return [{"id": key, "label": value["label"]} for key, value in CONCEITOS.items()]
