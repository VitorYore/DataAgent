import pandas as pd


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def normalizar_texto(texto: str) -> str:

    import unicodedata

    texto = str(texto).lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = (
        texto
        .replace("_", " ")
        .replace("-", " ")
    )

    texto = " ".join(
        texto.split()
    )

    return texto


def procurar_tabela(
    tabelas: dict[str, pd.DataFrame],
    nomes_possiveis: list[str]
):

    nomes_normalizados = [
        normalizar_texto(nome)
        for nome in nomes_possiveis
    ]

    for nome_tabela, df in tabelas.items():

        nome_normalizado = (
            normalizar_texto(
                nome_tabela
            )
        )

        if nome_normalizado in (
            nomes_normalizados
        ):

            return nome_tabela, df

    return None, None


def procurar_coluna(
    df: pd.DataFrame,
    nomes_possiveis: list[str]
):

    mapa_colunas = {
        normalizar_texto(coluna): coluna
        for coluna in df.columns
    }

    for nome in nomes_possiveis:

        nome_normalizado = (
            normalizar_texto(
                nome
            )
        )

        if (
            nome_normalizado
            in mapa_colunas
        ):

            return mapa_colunas[
                nome_normalizado
            ]

    return None


def merge_seguro(
    df_base: pd.DataFrame,
    agregado: pd.DataFrame,
    coluna_base: str,
    coluna_agregado: str
):

    linhas_antes = len(
        df_base
    )

    resultado = pd.merge(
        df_base,
        agregado,
        how="left",
        left_on=coluna_base,
        right_on=coluna_agregado,
        validate="many_to_one"
    )

    if (
        coluna_base != coluna_agregado
        and coluna_agregado
        in resultado.columns
    ):

        resultado = resultado.drop(
            columns=[
                coluna_agregado
            ]
        )

    linhas_depois = len(
        resultado
    )

    if linhas_antes != linhas_depois:

        raise ValueError(
            "O enriquecimento alterou a "
            "quantidade de linhas de "
            f"{linhas_antes} para "
            f"{linhas_depois}."
        )

    return resultado


def filtrar_ids_validos(
    dados: pd.DataFrame,
    coluna_dados: str,
    df_base: pd.DataFrame,
    coluna_base: str
):

    ids_validos = set(
        df_base[
            coluna_base
        ]
        .dropna()
        .unique()
    )

    return dados[
        dados[
            coluna_dados
        ].isin(
            ids_validos
        )
    ].copy()


# =========================================================
# AVALIAÇÕES
# =========================================================

def enriquecer_avaliacoes(
    df_base: pd.DataFrame,
    tabelas: dict[str, pd.DataFrame]
):

    nome_tabela, df = procurar_tabela(
        tabelas,
        [
            "Avaliacoes",
            "Avaliações",
            "Avaliacao",
            "Avaliação"
        ]
    )

    if df is None:

        return df_base, {
            "modulo": "avaliacoes",
            "status": "ignorado",
            "motivo": (
                "Tabela de avaliações "
                "não encontrada."
            )
        }

    produto_id = procurar_coluna(
        df,
        [
            "Produto_ID",
            "Produto ID",
            "ID Produto"
        ]
    )

    avaliacao = procurar_coluna(
        df,
        [
            "Avaliacao",
            "Avaliação",
            "Nota",
            "Rating"
        ]
    )

    if (
        not produto_id
        or not avaliacao
    ):

        return df_base, {
            "modulo": "avaliacoes",
            "status": "ignorado",
            "motivo": (
                "Não foi possível identificar "
                "Produto_ID e avaliação."
            )
        }

    if "Produto_ID" not in (
        df_base.columns
    ):

        return df_base, {
            "modulo": "avaliacoes",
            "status": "ignorado",
            "motivo": (
                "Produto_ID não existe no "
                "dataset principal."
            )
        }

    dados = df[
        [
            produto_id,
            avaliacao
        ]
    ].copy()

    dados[
        avaliacao
    ] = pd.to_numeric(
        dados[avaliacao],
        errors="coerce"
    )

    dados = dados.dropna(
        subset=[
            produto_id,
            avaliacao
        ]
    )

    # ========================================
    # CONSIDERAR SOMENTE PRODUTOS
    # REALMENTE PRESENTES NA BASE
    # ========================================

    registros_antes = len(
        dados
    )

    dados = filtrar_ids_validos(
        dados,
        produto_id,
        df_base,
        "Produto_ID"
    )

    registros_ignorados = (
        registros_antes
        - len(dados)
    )

    if dados.empty:

        return df_base, {
            "modulo": "avaliacoes",
            "status": "ignorado",
            "motivo": (
                "Nenhuma avaliação corresponde "
                "aos produtos da base principal."
            )
        }

    agregado = (
        dados
        .groupby(
            produto_id
        )
        .agg(
            Avaliacao_Media=(
                avaliacao,
                "mean"
            ),
            Quantidade_Avaliacoes=(
                avaliacao,
                "count"
            )
        )
        .reset_index()
    )

    agregado[
        "Avaliacao_Media"
    ] = (
        agregado[
            "Avaliacao_Media"
        ]
        .round(2)
    )

    resultado = merge_seguro(
        df_base,
        agregado,
        "Produto_ID",
        produto_id
    )

    # Produto sem avaliação
    # continua sem avaliação.
    # Não transformamos nota ausente em 0.

    resultado[
        "Quantidade_Avaliacoes"
    ] = (
        resultado[
            "Quantidade_Avaliacoes"
        ]
        .fillna(0)
        .astype(int)
    )

    return resultado, {
        "modulo": "avaliacoes",
        "status": "sucesso",
        "tabela": nome_tabela,

        "produtos_analisados": int(
            agregado[
                produto_id
            ].nunique()
        ),

        "registros_avaliacao_validos": int(
            len(dados)
        ),

        "registros_ignorados": int(
            registros_ignorados
        ),

        "colunas_adicionadas": [
            "Avaliacao_Media",
            "Quantidade_Avaliacoes"
        ]
    }


# =========================================================
# STOCK / ESTOQUE
# =========================================================

def enriquecer_stock(
    df_base: pd.DataFrame,
    tabelas: dict[str, pd.DataFrame]
):

    nome_tabela, df = procurar_tabela(
        tabelas,
        [
            "Stock",
            "Estoque"
        ]
    )

    if df is None:

        return df_base, {
            "modulo": "stock",
            "status": "ignorado",
            "motivo": (
                "Tabela de stock "
                "não encontrada."
            )
        }

    produto_id = procurar_coluna(
        df,
        [
            "Produto_ID",
            "Produto ID",
            "ID Produto"
        ]
    )

    estoque_atual = procurar_coluna(
        df,
        [
            "Estoque Atual",
            "Stock Atual",
            "Quantidade Atual",
            "Quantidade em stock",
            "Quantidade em estoque",
            "Stock",
            "Estoque"
        ]
    )

    estoque_minimo = procurar_coluna(
        df,
        [
            "Estoque Minimo",
            "Estoque Mínimo",
            "Stock Minimo",
            "Stock Mínimo",
            "Nivel Minimo",
            "Nível Mínimo",
            "Minimo",
            "Mínimo"
        ]
    )

    estoque_maximo = procurar_coluna(
        df,
        [
            "Estoque Maximo",
            "Estoque Máximo",
            "Stock Maximo",
            "Stock Máximo",
            "Nivel Maximo",
            "Nível Máximo",
            "Maximo",
            "Máximo"
        ]
    )

    tempo_entrega = procurar_coluna(
        df,
        [
            "Tempo Medio de Entrega (dias)",
            "Tempo Médio de Entrega (dias)",
            "Tempo Medio Entrega",
            "Tempo Médio Entrega"
        ]
    )

    if (
        not produto_id
        or not estoque_atual
    ):

        return df_base, {
            "modulo": "stock",
            "status": "ignorado",
            "motivo": (
                "Não foi possível identificar "
                "Produto_ID e estoque atual."
            )
        }

    if "Produto_ID" not in (
        df_base.columns
    ):

        return df_base, {
            "modulo": "stock",
            "status": "ignorado",
            "motivo": (
                "Produto_ID não existe no "
                "dataset principal."
            )
        }

    colunas = [
        produto_id,
        estoque_atual
    ]

    for coluna in [
        estoque_minimo,
        estoque_maximo,
        tempo_entrega
    ]:

        if coluna:

            colunas.append(
                coluna
            )

    dados = df[
        list(
            dict.fromkeys(
                colunas
            )
        )
    ].copy()

    dados = filtrar_ids_validos(
        dados,
        produto_id,
        df_base,
        "Produto_ID"
    )

    colunas_numericas = [
        estoque_atual,
        estoque_minimo,
        estoque_maximo,
        tempo_entrega
    ]

    for coluna in colunas_numericas:

        if coluna:

            dados[
                coluna
            ] = pd.to_numeric(
                dados[coluna],
                errors="coerce"
            )

    # ========================================
    # UM REGISTRO POR PRODUTO
    #
    # Stock é estado atual, portanto
    # não devemos somar caso exista
    # duplicidade acidental.
    # ========================================

    agregacoes = {
        estoque_atual: "last"
    }

    if estoque_minimo:

        agregacoes[
            estoque_minimo
        ] = "last"

    if estoque_maximo:

        agregacoes[
            estoque_maximo
        ] = "last"

    if tempo_entrega:

        agregacoes[
            tempo_entrega
        ] = "mean"

    agregado = (
        dados
        .groupby(
            produto_id,
            as_index=False
        )
        .agg(
            agregacoes
        )
    )

    renomear = {
        estoque_atual: (
            "Estoque_Atual"
        )
    }

    if estoque_minimo:

        renomear[
            estoque_minimo
        ] = "Estoque_Minimo"

    if estoque_maximo:

        renomear[
            estoque_maximo
        ] = "Estoque_Maximo"

    if tempo_entrega:

        renomear[
            tempo_entrega
        ] = "Tempo_Medio_Entrega_Dias"

    agregado = agregado.rename(
        columns=renomear
    )

    # ========================================
    # INDICADORES DE STOCK
    # ========================================

    if (
        "Estoque_Minimo"
        in agregado.columns
    ):

        agregado[
            "Risco_Ruptura"
        ] = (
            agregado[
                "Estoque_Atual"
            ]
            <= agregado[
                "Estoque_Minimo"
            ]
        )

    if (
        "Estoque_Maximo"
        in agregado.columns
    ):

        agregado[
            "Estoque_Excessivo"
        ] = (
            agregado[
                "Estoque_Atual"
            ]
            >= agregado[
                "Estoque_Maximo"
            ]
        )

    resultado = merge_seguro(
        df_base,
        agregado,
        "Produto_ID",
        produto_id
    )

    novas_colunas = [
        coluna
        for coluna in (
            agregado.columns
        )
        if coluna != produto_id
    ]

    return resultado, {
        "modulo": "stock",
        "status": "sucesso",
        "tabela": nome_tabela,

        "produtos_analisados": int(
            agregado[
                produto_id
            ].nunique()
        ),

        "colunas_adicionadas": (
            novas_colunas
        )
    }


# =========================================================
# DEVOLUÇÕES
# =========================================================

def enriquecer_devolucoes(
    df_base: pd.DataFrame,
    tabelas: dict[str, pd.DataFrame]
):

    nome_tabela, df = procurar_tabela(
        tabelas,
        [
            "Devolucoes",
            "Devoluções",
            "Devolucao",
            "Devolução"
        ]
    )

    if df is None:

        return df_base, {
            "modulo": "devolucoes",
            "status": "ignorado",
            "motivo": (
                "Tabela de devoluções "
                "não encontrada."
            )
        }

    produto_id = procurar_coluna(
        df,
        [
            "Produto_ID",
            "Produto ID",
            "ID Produto"
        ]
    )

    quantidade = procurar_coluna(
        df,
        [
            "Quantidade",
            "Quantidade Devolvida",
            "Qtd Devolvida",
            "Qtd"
        ]
    )

    motivo = procurar_coluna(
        df,
        [
            "Motivo",
            "Motivo da Devolução",
            "Motivo Devolucao",
            "Motivo Devolução"
        ]
    )

    if not produto_id:

        return df_base, {
            "modulo": "devolucoes",
            "status": "ignorado",
            "motivo": (
                "Não foi possível identificar "
                "Produto_ID."
            )
        }

    if "Produto_ID" not in (
        df_base.columns
    ):

        return df_base, {
            "modulo": "devolucoes",
            "status": "ignorado",
            "motivo": (
                "Produto_ID não existe no "
                "dataset principal."
            )
        }

    dados = filtrar_ids_validos(
        df.copy(),
        produto_id,
        df_base,
        "Produto_ID"
    )

    # ========================================
    # QUANTIDADE DEVOLVIDA
    # ========================================

    if quantidade:

        dados[
            quantidade
        ] = pd.to_numeric(
            dados[quantidade],
            errors="coerce"
        ).fillna(0)

        agregado = (
            dados
            .groupby(
                produto_id
            )
            .agg(
                Quantidade_Devolvida=(
                    quantidade,
                    "sum"
                ),
                Numero_Devolucoes=(
                    produto_id,
                    "size"
                )
            )
            .reset_index()
        )

    else:

        agregado = (
            dados
            .groupby(
                produto_id
            )
            .size()
            .reset_index(
                name=(
                    "Numero_Devolucoes"
                )
            )
        )

        agregado[
            "Quantidade_Devolvida"
        ] = agregado[
            "Numero_Devolucoes"
        ]

    # ========================================
    # MOTIVO PRINCIPAL
    # ========================================

    if motivo:

        def motivo_principal(
            serie
        ):

            moda = (
                serie
                .dropna()
                .mode()
            )

            if moda.empty:

                return None

            return moda.iloc[0]

        motivos = (
            dados
            .groupby(
                produto_id
            )[motivo]
            .agg(
                motivo_principal
            )
            .reset_index()
            .rename(
                columns={
                    motivo: (
                        "Principal_Motivo_Devolucao"
                    )
                }
            )
        )

        agregado = pd.merge(
            agregado,
            motivos,
            how="left",
            on=produto_id,
            validate="one_to_one"
        )

    resultado = merge_seguro(
        df_base,
        agregado,
        "Produto_ID",
        produto_id
    )

    # ========================================
    # PRODUTO SEM DEVOLUÇÃO = ZERO
    # ========================================

    resultado[
        "Quantidade_Devolvida"
    ] = (
        resultado[
            "Quantidade_Devolvida"
        ]
        .fillna(0)
    )

    resultado[
        "Numero_Devolucoes"
    ] = (
        resultado[
            "Numero_Devolucoes"
        ]
        .fillna(0)
        .astype(int)
    )

    # ========================================
    # TAXA DE DEVOLUÇÃO
    # ========================================

    if "Quantidade" in (
        resultado.columns
    ):

        vendidos = (
            resultado
            .groupby(
                "Produto_ID"
            )["Quantidade"]
            .transform(
                "sum"
            )
        )

        resultado[
            "Taxa_Devolucao"
        ] = 0.0

        mascara = (
            vendidos > 0
        )

        resultado.loc[
            mascara,
            "Taxa_Devolucao"
        ] = (
            resultado.loc[
                mascara,
                "Quantidade_Devolvida"
            ]
            / vendidos[
                mascara
            ]
            * 100
        )

        resultado[
            "Taxa_Devolucao"
        ] = (
            resultado[
                "Taxa_Devolucao"
            ]
            .round(2)
        )

    novas_colunas = [
        coluna
        for coluna in (
            agregado.columns
        )
        if coluna != produto_id
    ]

    if (
        "Taxa_Devolucao"
        in resultado.columns
    ):

        novas_colunas.append(
            "Taxa_Devolucao"
        )

    return resultado, {
        "modulo": "devolucoes",
        "status": "sucesso",
        "tabela": nome_tabela,

        "produtos_analisados": int(
            agregado[
                produto_id
            ].nunique()
        ),

        "produtos_sem_devolucao": int(
            df_base[
                "Produto_ID"
            ]
            .nunique()
            - agregado[
                produto_id
            ]
            .nunique()
        ),

        "colunas_adicionadas": (
            novas_colunas
        )
    }


# =========================================================
# ENRIQUECIMENTO COMPLETO
# =========================================================

def enriquecer_dataset(
    df_base: pd.DataFrame,
    tabelas: dict[str, pd.DataFrame]
):

    df = df_base.copy()

    logs = []

    # ========================================
    # AVALIAÇÕES
    # ========================================

    try:

        df, log = (
            enriquecer_avaliacoes(
                df,
                tabelas
            )
        )

        logs.append(
            log
        )

    except Exception as erro:

        logs.append({
            "modulo": "avaliacoes",
            "status": "erro",
            "motivo": str(
                erro
            )
        })

    # ========================================
    # STOCK
    # ========================================

    try:

        df, log = (
            enriquecer_stock(
                df,
                tabelas
            )
        )

        logs.append(
            log
        )

    except Exception as erro:

        logs.append({
            "modulo": "stock",
            "status": "erro",
            "motivo": str(
                erro
            )
        })

    # ========================================
    # DEVOLUÇÕES
    # ========================================

    try:

        df, log = (
            enriquecer_devolucoes(
                df,
                tabelas
            )
        )

        logs.append(
            log
        )

    except Exception as erro:

        logs.append({
            "modulo": "devolucoes",
            "status": "erro",
            "motivo": str(
                erro
            )
        })

    return df, logs