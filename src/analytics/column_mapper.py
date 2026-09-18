import re
import unicodedata

import pandas as pd


# ========================================
# REGRAS GENÉRICAS
# ========================================

REGRAS = {

    # ========================================
    # FINANCEIRO
    # ========================================

    "faturamento": {
        "palavras": [
            "faturamento",
            "faturamento_calculado",
            "receita",
            "receita_total",
            "valor_liquido",
            "valor_venda",
            "total_venda",
            "total_vendas"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "valor_total": {
        "palavras": ["valor_total", "valor_bruto"],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "valor_com_desconto": {
        "palavras": ["valor_com_desconto", "valor_c_desconto", "valor_descontado"],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "custo": {
        "palavras": [
            "custo_total",
            "custo_total_calculado",
            "total_custo",
            "despesa_total"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "custo_unitario": {
        "palavras": [
            "custo_unitario",
            "custo_aquisicao",
            "custo_de_aquisicao",
            "unit_cost"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    "lucro": {
        "palavras": [
            "lucro",
            "lucro_total",
            "lucro_calculado",
            "profit"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "margem_bruta": {
        "palavras": ["margem_bruta", "lucro_bruto"],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "margem_bruta_percentual": {
        "palavras": ["margem_bruta_percentual", "percentual_margem_bruta"],
        "tipo": "percentual",
        "agregacao": None
    },

    "margem_lucro": {
        "palavras": [
            "margem_lucro",
            "margem_de_lucro",
            "margem_lucro_calculada"
        ],
        "tipo": "percentual",
        "agregacao": "mean"
    },

    # ========================================
    # VENDA
    # ========================================

    "quantidade": {
        "palavras": [
            "quantidade",
            "qtd",
            "qtde",
            "quantity",
            "unidades",
            "volume"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "preco_unitario": {
        "palavras": [
            "preco_unitario",
            "preco_unidade",
            "valor_unitario",
            "unit_price",
            "unitprice"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    # ========================================
    # NOVAS MÉTRICAS ENRIQUECIDAS
    # ========================================

    "avaliacao_media": {
        "palavras": [
            "avaliacao_media",
            "nota_media",
            "rating_medio"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    "quantidade_avaliacoes": {
        "palavras": [
            "quantidade_avaliacoes",
            "numero_avaliacoes",
            "total_avaliacoes"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "estoque_atual": {
        "palavras": [
            "estoque_atual",
            "stock_atual"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    "estoque_minimo": {
        "palavras": [
            "estoque_minimo",
            "stock_minimo"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    "estoque_maximo": {
        "palavras": [
            "estoque_maximo",
            "stock_maximo"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    "tempo_entrega": {
        "palavras": [
            "tempo_medio_entrega_dias",
            "tempo_entrega",
            "prazo_entrega"
        ],
        "tipo": "metrica",
        "agregacao": "mean"
    },

    "risco_ruptura": {
        "palavras": [
            "risco_ruptura"
        ],
        "tipo": "indicador",
        "agregacao": None
    },

    "estoque_excessivo": {
        "palavras": [
            "estoque_excessivo"
        ],
        "tipo": "indicador",
        "agregacao": None
    },

    "quantidade_devolvida": {
        "palavras": [
            "quantidade_devolvida",
            "qtd_devolvida"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "numero_devolucoes": {
        "palavras": [
            "numero_devolucoes",
            "quantidade_devolucoes"
        ],
        "tipo": "metrica",
        "agregacao": "sum"
    },

    "taxa_devolucao": {
        "palavras": [
            "taxa_devolucao",
            "percentual_devolucao"
        ],
        "tipo": "percentual",
        "agregacao": "mean"
    },

    "motivo_devolucao": {
        "palavras": [
            "principal_motivo_devolucao",
            "motivo_devolucao"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    # ========================================
    # IDENTIFICADORES
    # ========================================

    "venda_id": {
        "palavras": [
            "venda_id",
            "id_venda"
        ],
        "tipo": "identificador",
        "agregacao": "nunique"
    },

    "pedido": {
        "palavras": [
            "pedido",
            "pedido_id",
            "id_pedido"
        ],
        "tipo": "identificador",
        "agregacao": "nunique"
    },

    "produto_id": {
        "palavras": [
            "produto_id",
            "id_produto"
        ],
        "tipo": "identificador_dimensao",
        "agregacao": "nunique"
    },

    "cliente_id": {
        "palavras": [
            "cliente_id",
            "id_cliente"
        ],
        "tipo": "identificador_dimensao",
        "agregacao": "nunique"
    },

    "loja_id": {
        "palavras": [
            "loja_id",
            "id_loja"
        ],
        "tipo": "identificador_dimensao",
        "agregacao": "nunique"
    },

    "colaborador_id": {
        "palavras": [
            "colaborador_id",
            "id_colaborador"
        ],
        "tipo": "identificador_dimensao",
        "agregacao": "nunique"
    },

    # ========================================
    # DIMENSÕES
    # ========================================

    "cliente": {
        "palavras": [
            "cliente",
            "nome_cliente"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "produto": {
        "palavras": [
            "produto",
            "nome_produto"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "categoria": {
        "palavras": [
            "categoria"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "loja": {
        "palavras": [
            "loja",
            "nome_loja"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "colaborador": {
        "palavras": [
            "colaborador",
            "nome_colaborador"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "regiao": {
        "palavras": [
            "regiao"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "cidade": {
        "palavras": [
            "cidade"
        ],
        "tipo": "dimensao",
        "agregacao": None
    },

    "canal_venda": {
        "palavras": [
            "canal_venda",
            "canal_de_venda"
        ],
        "tipo": "dimensao",
        "agregacao": "count"
    },

    "pagamento": {
        "palavras": [
            "pagamento",
            "forma_pagamento"
        ],
        "tipo": "dimensao",
        "agregacao": "count"
    },

    "status": {
        "palavras": [
            "status",
            "situacao"
        ],
        "tipo": "dimensao",
        "agregacao": "count"
    },

    # ========================================
    # TEMPORAIS
    # ========================================

    "data": {
        "palavras": [
            "data",
            "data_venda",
            "data_da_venda"
        ],
        "tipo": "temporal",
        "agregacao": None
    },

    "ano": {
        "palavras": [
            "ano"
        ],
        "tipo": "temporal",
        "agregacao": None
    },

    "mes": {
        "palavras": [
            "mes",
            "nome_mes"
        ],
        "tipo": "temporal",
        "agregacao": None
    },

    "trimestre": {
        "palavras": [
            "trimestre"
        ],
        "tipo": "temporal",
        "agregacao": None
    }
}


def normalizar_nome(nome: str) -> str:

    nome = str(nome).lower().strip().replace("%", " percentual ")

    nome = unicodedata.normalize(
        "NFKD",
        nome
    )

    nome = "".join(
        caractere
        for caractere in nome
        if not unicodedata.combining(
            caractere
        )
    )

    nome = re.sub(
        r"[^a-z0-9]+",
        "_",
        nome
    )

    return nome.strip("_")


def conceito_por_rotulo_cabecalho(rotulo: str, rotulos_contexto=None):
    """Resolve somente rótulos explícitos e não ambíguos para conceitos semânticos."""
    nome = normalizar_nome(rotulo)
    aliases = {
        "pedido": "pedido", "pedido_id": "pedido", "id_pedido": "pedido",
        "data": "data", "data_venda": "data", "data_da_venda": "data",
        "valor_total": "valor_total", "valor_bruto": "valor_total",
        "valor_com_desconto": "valor_com_desconto", "valor_c_desconto": "valor_com_desconto",
        "valor_descontado": "valor_com_desconto",
        "margem_bruta": "margem_bruta", "lucro_bruto": "margem_bruta",
        "margem_bruta_percentual": "margem_bruta_percentual",
        "percentual_margem_bruta": "margem_bruta_percentual",
        "forma_pagamento": "forma_pagamento", "forma_de_pagamento": "forma_pagamento",
        "pagamento": "forma_pagamento", "meio_de_pagamento": "forma_pagamento",
        "cliente": "cliente",
    }
    if nome == "valor_liquido":
        contexto = {normalizar_nome(rotulo) for rotulo in (rotulos_contexto or [])}
        return "valor_com_desconto" if any("desconto" in item for item in contexto) and "valor_total" in contexto else None
    if nome == "total":
        return None
    return aliases.get(nome)


def separar_contexto(
    nome_coluna: str
):

    if "__" not in nome_coluna:

        return (
            None,
            normalizar_nome(
                nome_coluna
            )
        )

    origem, coluna = (
        nome_coluna.split(
            "__",
            1
        )
    )

    return (
        normalizar_nome(origem),
        normalizar_nome(coluna)
    )


def classificar_por_contexto(
    nome_coluna: str
):

    origem, coluna = separar_contexto(
        nome_coluna
    )

    if not origem:
        return None

    # ========================================
    # PRODUTOS
    # ========================================

    if origem == "produtos":

        if coluna == "nome":

            return {
                "papel": "produto",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "categoria":

            return {
                "papel": "categoria",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna in [
            "custo_aquisicao",
            "custo_de_aquisicao"
        ]:

            return {
                "papel": "custo_unitario",
                "tipo": "metrica",
                "agregacao": "mean",
                "confianca": 100
            }

        if coluna == "preco":

            return {
                "papel": "preco_unitario",
                "tipo": "metrica",
                "agregacao": "mean",
                "confianca": 80
            }

        if coluna == "cor":

            return {
                "papel": "cor_produto",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "tamanho":

            return {
                "papel": "tamanho_produto",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

    # ========================================
    # CLIENTES
    # ========================================

    if origem == "clientes":

        if coluna == "nome":

            return {
                "papel": "cliente",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "cidade":

            return {
                "papel": "cidade_cliente",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna in [
            "genero",
            "sexo"
        ]:

            return {
                "papel": "genero_cliente",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "canal_de_compra":

            return {
                "papel": "canal_compra",
                "tipo": "dimensao",
                "agregacao": "count",
                "confianca": 100
            }

    # ========================================
    # LOJAS
    # ========================================

    if origem == "lojas":

        if coluna == "nome":

            return {
                "papel": "loja",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "regiao":

            return {
                "papel": "regiao",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "cidade":

            return {
                "papel": "cidade_loja",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "tipo":

            return {
                "papel": "tipo_loja",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

    # ========================================
    # COLABORADORES
    # ========================================

    if origem == "colaboradores":

        if coluna == "nome":

            return {
                "papel": "colaborador",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna in [
            "funcao",
            "cargo"
        ]:

            return {
                "papel": "funcao_colaborador",
                "tipo": "dimensao",
                "agregacao": None,
                "confianca": 100
            }

        if coluna == "loja_id":

            return {
                "papel": "loja_id",
                "tipo": "identificador_dimensao",
                "agregacao": "nunique",
                "confianca": 80
            }

    return None


def classificar_coluna_enriquecida(
    nome_coluna: str
):

    nome = normalizar_nome(
        nome_coluna
    )

    regras_diretas = {

        "avaliacao_media": (
            "avaliacao_media",
            "metrica",
            "mean"
        ),

        "quantidade_avaliacoes": (
            "quantidade_avaliacoes",
            "metrica",
            "sum"
        ),

        "estoque_atual": (
            "estoque_atual",
            "metrica",
            "mean"
        ),

        "estoque_minimo": (
            "estoque_minimo",
            "metrica",
            "mean"
        ),

        "estoque_maximo": (
            "estoque_maximo",
            "metrica",
            "mean"
        ),

        "tempo_medio_entrega_dias": (
            "tempo_entrega",
            "metrica",
            "mean"
        ),

        "risco_ruptura": (
            "risco_ruptura",
            "indicador",
            None
        ),

        "estoque_excessivo": (
            "estoque_excessivo",
            "indicador",
            None
        ),

        "quantidade_devolvida": (
            "quantidade_devolvida",
            "metrica",
            "sum"
        ),

        "numero_devolucoes": (
            "numero_devolucoes",
            "metrica",
            "sum"
        ),

        "principal_motivo_devolucao": (
            "motivo_devolucao",
            "dimensao",
            None
        ),

        "taxa_devolucao": (
            "taxa_devolucao",
            "percentual",
            "mean"
        )
    }

    if nome not in regras_diretas:
        return None

    papel, tipo, agregacao = (
        regras_diretas[nome]
    )

    return {
        "papel": papel,
        "tipo": tipo,
        "agregacao": agregacao,
        "confianca": 100
    }


def calcular_score_nome(
    nome_coluna: str,
    palavras: list[str]
) -> int:

    nome = normalizar_nome(
        nome_coluna
    )

    partes = nome.split("_")

    melhor_score = 0

    for palavra in palavras:

        palavra = normalizar_nome(
            palavra
        )

        if nome == palavra:
            score = 80

        elif (
            "_" in palavra
            and palavra in nome
        ):
            score = 70

        elif palavra in partes:
            score = 50

        elif palavra in nome:
            score = 20

        else:
            score = 0

        melhor_score = max(
            melhor_score,
            score
        )

    return melhor_score


def calcular_score_tipo(
    serie: pd.Series,
    papel: str
) -> int:

    papeis_numericos = [
        "faturamento",
        "valor_total",
        "valor_com_desconto",
        "margem_bruta",
        "margem_bruta_percentual",
        "custo",
        "custo_unitario",
        "lucro",
        "margem_lucro",
        "quantidade",
        "preco_unitario",
        "avaliacao_media",
        "quantidade_avaliacoes",
        "estoque_atual",
        "estoque_minimo",
        "estoque_maximo",
        "tempo_entrega",
        "quantidade_devolvida",
        "numero_devolucoes",
        "taxa_devolucao"
    ]

    if (
        papel in papeis_numericos
        and pd.api.types.is_numeric_dtype(
            serie
        )
    ):
        return 20

    if papel == "data":

        if pd.api.types.is_datetime64_any_dtype(
            serie
        ):
            return 20

    if papel in [
        "pedido",
        "venda_id"
    ]:

        if len(serie) > 0:

            proporcao = (
                serie.nunique()
                / len(serie)
            )

            if proporcao >= 0.70:
                return 20

    if papel in [
        "produto_id",
        "cliente_id",
        "loja_id",
        "colaborador_id"
    ]:
        return 20

    if pd.api.types.is_object_dtype(
        serie
    ):
        return 10

    return 0


def classificar_coluna(
    nome_coluna: str,
    serie: pd.Series
) -> dict:

    # ========================================
    # 1. COLUNAS ENRIQUECIDAS
    # ========================================

    enriquecida = (
        classificar_coluna_enriquecida(
            nome_coluna
        )
    )

    if enriquecida:
        return enriquecida

    # ========================================
    # 2. CONTEXTO DE MERGE
    # ========================================

    contextual = classificar_por_contexto(
        nome_coluna
    )

    if contextual:
        return contextual

    # ========================================
    # 3. REGRAS GENÉRICAS
    # ========================================

    melhor_papel = None
    melhor_score = 0
    melhor_regra = None

    for papel, regra in REGRAS.items():

        score_nome = calcular_score_nome(
            nome_coluna,
            regra["palavras"]
        )

        score_tipo = calcular_score_tipo(
            serie,
            papel
        )

        score = min(
            score_nome + score_tipo,
            100
        )

        if score > melhor_score:

            melhor_score = score
            melhor_papel = papel
            melhor_regra = regra

    if melhor_score < 50:

        return {
            "papel": "desconhecido",
            "tipo": "desconhecido",
            "agregacao": None,
            "confianca": melhor_score
        }

    return {
        "papel": melhor_papel,
        "tipo": melhor_regra["tipo"],
        "agregacao": melhor_regra["agregacao"],
        "confianca": melhor_score
    }


def mapear_colunas(
    df: pd.DataFrame
) -> dict:

    mapeamento = {}

    for coluna in df.columns:

        mapeamento[coluna] = (
            classificar_coluna(
                coluna,
                df[coluna]
            )
        )

    return mapeamento