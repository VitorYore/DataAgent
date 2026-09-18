import re
import pandas as pd

from src.analytics.column_mapper import (
    conceito_por_rotulo_cabecalho,
    mapear_colunas
)


def encontrar_coluna_por_papel(
    mapeamento: dict,
    papel: str
):

    candidatos = []

    for coluna, dados in (
        mapeamento.items()
    ):

        if dados.get(
            "papel"
        ) != papel:

            continue

        candidatos.append({
            "coluna": coluna,
            "confianca": dados.get(
                "confianca",
                0
            )
        })

    if not candidatos:

        return None

    candidatos.sort(
        key=lambda item: item[
            "confianca"
        ],
        reverse=True
    )

    return candidatos[0][
        "coluna"
    ]


def _normalizacoes_ingestao(df):
    ingestao = df.attrs.get("ingestao", {})
    structures = [ingestao] if isinstance(ingestao, dict) else []
    if isinstance(ingestao, dict):
        structures.extend(value for value in ingestao.values() if isinstance(value, dict))
    for structure in structures:
        meta = structure.get("normalizacao")
        if isinstance(meta, dict):
            yield meta


def _indice_coluna_excel(letras):
    indice = 0
    for letra in letras.upper():
        indice = indice * 26 + ord(letra) - ord("A") + 1
    return indice


def _margem_bruta_percentual_por_formulas(df, mapeamento):
    """Pondera linhas usando somente a base comprovada pela f?rmula de origem."""
    numerator_column = encontrar_coluna_por_papel(mapeamento, "margem_bruta")
    if not numerator_column:
        return None
    rows_by_base = {"valor_total": [], "valor_com_desconto": []}
    for meta in _normalizacoes_ingestao(df):
        labels_by_position = {}
        for header in meta.get("evidencias_cabecalho_tardio", []):
            if not header.get("validado"):
                continue
            labels = [item.get("rotulo") for item in header.get("colunas", [])]
            for item in header.get("colunas", []):
                if item.get("mapeamento_permitido"):
                    concept = conceito_por_rotulo_cabecalho(item.get("rotulo", ""), labels)
                    if concept:
                        labels_by_position[item["posicao"]] = concept
        mappings = {**df.attrs.get("mapeamentos_automaticos", {}), **df.attrs.get("mapeamentos_confirmados", {})}
        for field, concept in mappings.items():
            match_column = re.fullmatch(r"coluna_(\d+)", str(field))
            if match_column:
                labels_by_position[int(match_column.group(1))] = concept
        if not labels_by_position:
            continue
        source_rows = [row for block in meta.get("blocos", []) for row in block.get("linhas_origem", [])]
        row_positions = {row: index for index, row in enumerate(source_rows)}
        formulas = meta.get("evidencias_excel", {}).get("formulas", []) or meta.get("formulas_indisponiveis", [])
        for item in formulas:
            match = re.fullmatch(r"=\s*\$?([A-Z]{1,3})\$?\d+\s*/\s*\$?([A-Z]{1,3})\$?\d+", str(item.get("formula", "")).strip(), re.I)
            if not match:
                continue
            formula_position = int(item.get("coluna", 0))
            numerator_position = _indice_coluna_excel(match.group(1))
            denominator_position = _indice_coluna_excel(match.group(2))
            if labels_by_position.get(formula_position) != "margem_bruta_percentual":
                continue
            if labels_by_position.get(numerator_position) != "margem_bruta":
                continue
            base = labels_by_position.get(denominator_position)
            row_index = row_positions.get(item.get("linha"))
            if base in rows_by_base and row_index is not None and row_index < len(df):
                rows_by_base[base].append(row_index)

    bases_com_formula = [base for base, indices in rows_by_base.items() if indices]
    # O percentual n?o tem um agregado ?nico quando blocos diferentes usam bases distintas.
    if len(bases_com_formula) != 1:
        return None
    total_numerator = total_denominator = 0.0
    valid_rows = 0
    for base, row_indices in rows_by_base.items():
        denominator_column = encontrar_coluna_por_papel(mapeamento, base)
        if not row_indices or not denominator_column:
            continue
        unique_indices = list(dict.fromkeys(row_indices))
        numerator = pd.to_numeric(df.iloc[unique_indices][numerator_column], errors="coerce")
        denominator = pd.to_numeric(df.iloc[unique_indices][denominator_column], errors="coerce")
        valid = numerator.notna() & denominator.notna() & denominator.ne(0)
        if valid.any():
            total_numerator += float(numerator[valid].sum())
            total_denominator += float(denominator[valid].sum())
            valid_rows += int(valid.sum())
    if not valid_rows or total_denominator == 0:
        return None
    return round(total_numerator / total_denominator * 100, 2), valid_rows


def calcular_kpis(
    df: pd.DataFrame
) -> dict:

    mapeamento = mapear_colunas(
        df
    )

    coluna_faturamento = (
        encontrar_coluna_por_papel(
            mapeamento,
            "faturamento"
        )
    )

    coluna_custo = (
        encontrar_coluna_por_papel(
            mapeamento,
            "custo"
        )
    )

    coluna_lucro = (
        encontrar_coluna_por_papel(
            mapeamento,
            "lucro"
        )
    )

    coluna_valor_total = encontrar_coluna_por_papel(mapeamento, "valor_total")
    coluna_valor_com_desconto = encontrar_coluna_por_papel(mapeamento, "valor_com_desconto")
    coluna_margem_bruta = encontrar_coluna_por_papel(mapeamento, "margem_bruta")
    coluna_margem_bruta_percentual = encontrar_coluna_por_papel(mapeamento, "margem_bruta_percentual")

    coluna_quantidade = (
        encontrar_coluna_por_papel(
            mapeamento,
            "quantidade"
        )
    )

    coluna_venda = (
        encontrar_coluna_por_papel(
            mapeamento,
            "venda_id"
        )
    )

    if not coluna_venda:

        coluna_venda = (
            encontrar_coluna_por_papel(
                mapeamento,
                "pedido"
            )
        )

    resultado = {}

    # ========================================
    # FATURAMENTO
    # ========================================

    faturamento = None

    if coluna_faturamento:

        faturamento = (
            df[coluna_faturamento]
            .sum()
        )

        resultado[
            "faturamento_total"
        ] = round(
            float(faturamento),
            2
        )

    if coluna_valor_total:
        resultado["valor_total"] = round(float(df[coluna_valor_total].sum(min_count=1)), 2)

    if coluna_valor_com_desconto:
        total_descontado = df[coluna_valor_com_desconto].sum(min_count=1)
        if pd.notna(total_descontado):
            resultado["valor_com_desconto"] = round(float(total_descontado), 2)

    if coluna_margem_bruta:
        margem_bruta = df[coluna_margem_bruta].sum(min_count=1)
        if pd.notna(margem_bruta):
            resultado["margem_bruta"] = round(float(margem_bruta), 2)

    if coluna_margem_bruta_percentual:
        valores_percentuais = pd.to_numeric(df[coluna_margem_bruta_percentual], errors="coerce").dropna()
        if not valores_percentuais.empty:
            # Percentuais não são somados nem promediados sem uma base ponderadora.
            bases = [col for col in (coluna_valor_total, coluna_valor_com_desconto) if col]
            if len(bases) == 1:
                pesos = pd.to_numeric(df.loc[valores_percentuais.index, bases[0]], errors="coerce")
                validos = pesos.notna() & pesos.ne(0)
                if validos.any():
                    resultado["margem_bruta_percentual"] = round(
                        float((valores_percentuais[validos] * pesos[validos]).sum() / pesos[validos].sum()), 2
                    )
                    resultado["margem_bruta_percentual_metodo"] = "media_ponderada_pela_base_semantica_unica"

    percentual_formula = _margem_bruta_percentual_por_formulas(df, mapeamento)
    if percentual_formula:
        resultado["margem_bruta_percentual"] = percentual_formula[0]
        resultado["margem_bruta_percentual_metodo"] = "ponderada_por_soma_da_margem_e_base_referenciada_em_formula"
        resultado["margem_bruta_percentual_linhas_base"] = percentual_formula[1]

    resultado["quantidade_registros"] = int(len(df))

    # ========================================
    # CUSTO
    # ========================================

    custo = None

    if coluna_custo:

        custo = (
            df[coluna_custo]
            .sum()
        )

        resultado[
            "custo_total"
        ] = round(
            float(custo),
            2
        )

    # ========================================
    # LUCRO
    # ========================================

    lucro = None

    if coluna_lucro:

        lucro = (
            df[coluna_lucro]
            .sum()
        )

        resultado[
            "lucro_total"
        ] = round(
            float(lucro),
            2
        )

    # ========================================
    # QUANTIDADE VENDIDA
    # ========================================

    if coluna_quantidade:

        quantidade = (
            df[coluna_quantidade]
            .sum()
        )

        resultado[
            "quantidade_vendida"
        ] = round(
            float(quantidade),
            2
        )

    # ========================================
    # QUANTIDADE DE VENDAS / PEDIDOS
    # ========================================

    if coluna_venda:

        identificadores_validos = df[coluna_venda].dropna()
        if pd.api.types.is_object_dtype(identificadores_validos.dtype) or pd.api.types.is_string_dtype(identificadores_validos.dtype):
            identificadores_validos = identificadores_validos.astype(str).str.strip()
            identificadores_validos = identificadores_validos[
                identificadores_validos.ne("")
                & ~identificadores_validos.str.casefold().isin({"pedido", "total", "subtotal", "meta", "nan", "none"})
            ]
        quantidade_vendas = identificadores_validos.nunique()

        resultado[
            "quantidade_pedidos"
        ] = int(
            quantidade_vendas
        )

        # ====================================
        # TICKET MÉDIO
        # ====================================

        if (
            faturamento is not None
            and quantidade_vendas > 0
        ):

            ticket_medio = (
                faturamento
                / quantidade_vendas
            )

            resultado[
                "ticket_medio"
            ] = round(
                float(ticket_medio),
                2
            )

    # ========================================
    # MARGEM
    # ========================================

    if (
        lucro is not None
        and faturamento is not None
        and faturamento != 0
    ):

        margem = (
            lucro
            / faturamento
            * 100
        )

        resultado[
            "margem_lucro"
        ] = round(
            float(margem),
            2
        )

    return resultado