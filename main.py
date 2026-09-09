import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent

from pprint import pprint


# ========================================
# INGESTION
# ========================================

from src.ingestion.loader import carregar_dados

from src.ingestion.multi_loader import (
    encontrar_arquivos,
    carregar_multiplas_tabelas,
    gerar_resumo_tabelas
)


# ========================================
# RELACIONAMENTOS
# ========================================

from src.relationships.detector import (
    detectar_relacionamentos
)

from src.relationships.merger import (
    criar_dataset_analitico
)

from src.relationships.enricher import (
    enriquecer_dataset
)


# ========================================
# QUALIDADE
# ========================================

from src.quality.validator import gerar_diagnostico
from src.reports.data_quality import gerar_qualidade_dados
from src.quality.issues import gerar_problemas


# ========================================
# RELATÓRIOS
# ========================================

from src.reports.json_report import (
    salvar_relatorio
)

from src.reports.analysis_report import (
    salvar_analise
)

from src.reports.executive_summary import (
    gerar_resumo_executivo
)

from src.reports.executive_report import (
    salvar_resumo_executivo
)


# ========================================
# ETL
# ========================================

from src.etl.cleaner import executar_etl

from src.etl.exporter import (
    salvar_dados_tratados
)


# ========================================
# ANALYTICS
# ========================================

from src.analytics.column_mapper import (
    mapear_colunas
)

from src.analytics.business import (
    calcular_kpis
)

from src.analytics.temporal import (
    analisar_meses
)

from src.analytics.customers import (
    analisar_clientes
)

from src.analytics.performance import (
    analisar_desempenho
)

from src.analytics.growth import (
    analisar_crescimento
)

from src.analytics.dimensions import (
    analisar_dimensoes
)

from src.analytics.products import (
    analisar_produtos
)

from src.analytics.opportunities import (
    analisar_oportunidades
)

from src.analytics.insights import (
    gerar_insights
)

from src.analytics.derived_metrics import (
    criar_metricas_derivadas
)


# =========================================================
# RESUMO DAS TABELAS
# =========================================================


def exibir_resumo_tabelas(
    tabelas: dict
):

    resumo = gerar_resumo_tabelas(
        tabelas
    )

    print(
        "\n=== MODO MÚLTIPLAS TABELAS ===\n"
    )

    print(
        f"Tabelas carregadas: "
        f"{len(tabelas)}"
    )

    for nome_tabela, dados in (
        resumo.items()
    ):

        print(
            "\n" + "=" * 60
        )

        print(
            f"TABELA: {nome_tabela}"
        )

        print(
            "=" * 60
        )

        print(
            f"Linhas: "
            f"{dados['linhas']}"
        )

        print(
            f"Colunas: "
            f"{dados['colunas']}"
        )

        print(
            "\nColunas encontradas:"
        )

        for coluna in (
            dados[
                "nomes_colunas"
            ]
        ):

            print(
                f"- {coluna}"
            )


# =========================================================
# RELACIONAMENTOS
# =========================================================


def exibir_relacionamentos(
    relacionamentos: list
):

    print(
        "\n=== RELACIONAMENTOS IDENTIFICADOS ===\n"
    )

    if not relacionamentos:

        print(
            "Nenhum relacionamento confiável "
            "foi identificado."
        )

        return

    print(
        f"Relacionamentos encontrados: "
        f"{len(relacionamentos)}\n"
    )

    for indice, relacionamento in enumerate(
        relacionamentos,
        start=1
    ):

        tipo = relacionamento[
            "tipo_relacionamento"
        ]

        tabela_a = relacionamento[
            "tabela_a"
        ]

        coluna_a = relacionamento[
            "coluna_a"
        ]

        tabela_b = relacionamento[
            "tabela_b"
        ]

        coluna_b = relacionamento[
            "coluna_b"
        ]

        cobertura = relacionamento[
            "cobertura"
        ]

        confianca = relacionamento[
            "confianca"
        ]

        print(
            f"{indice}. "
            f"{tabela_a}.{coluna_a}"
        )

        print(
            "   ↓"
        )

        print(
            f"   {tabela_b}.{coluna_b}"
        )

        print(
            f"   Tipo: "
            f"{tipo}"
        )

        if tipo == "um_para_muitos":

            print(
                f"   PK: "
                f"{relacionamento['tabela_pk']}."
                f"{relacionamento['coluna_pk']}"
            )

            print(
                f"   FK: "
                f"{relacionamento['tabela_fk']}."
                f"{relacionamento['coluna_fk']}"
            )

        print(
            f"   Cobertura: "
            f"{cobertura}%"
        )

        print(
            f"   Confiança: "
            f"{confianca}%"
        )

        print()


# =========================================================
# MERGES
# =========================================================


def exibir_logs_merge(
    tabela_principal: str,
    df_analitico,
    logs_merge: list
):

    print(
        "\n=== CONSTRUÇÃO DO DATASET ANALÍTICO ===\n"
    )

    print(
        f"Tabela principal identificada: "
        f"{tabela_principal}"
    )

    print(
        f"\nLinhas do dataset analítico: "
        f"{len(df_analitico)}"
    )

    print(
        f"Colunas do dataset analítico: "
        f"{len(df_analitico.columns)}"
    )

    if not logs_merge:

        print(
            "\nNenhuma dimensão pôde "
            "ser adicionada automaticamente."
        )

        return

    print(
        "\n=== MERGES REALIZADOS ===\n"
    )

    for log in logs_merge:

        status = log[
            "status"
        ]

        if status == "sucesso":

            print(
                f"[SUCESSO] "
                f"{log['tabela_adicionada']}"
            )

            print(
                f"  FK: "
                f"{log['coluna_fk']}"
            )

            print(
                f"  PK: "
                f"{log['coluna_pk']}"
            )

            print(
                f"  Cobertura: "
                f"{log['cobertura']}%"
            )

            print(
                f"  Confiança: "
                f"{log['confianca']}%"
            )

            if (
                "score_dimensao"
                in log
            ):

                print(
                    f"  Score dimensão: "
                    f"{log['score_dimensao']}"
                )

            print(
                f"  Colunas adicionadas: "
                f"{log['colunas_adicionadas']}"
            )

            print(
                f"  Linhas após merge: "
                f"{log['linhas_resultado']}"
            )

            print()

        elif status == "ignorado":

            print(
                f"[IGNORADO] "
                f"{log['tabela_adicionada']}"
            )

            print(
                f"  Motivo: "
                f"{log['motivo']}"
            )

            print()


# =========================================================
# ENRIQUECIMENTO
# =========================================================


def exibir_logs_enriquecimento(
    df_antes,
    df_depois,
    logs: list
):

    print(
        "\n=== ENRIQUECIMENTO DO DATASET ===\n"
    )

    print(
        f"Linhas antes: "
        f"{len(df_antes)}"
    )

    print(
        f"Linhas depois: "
        f"{len(df_depois)}"
    )

    print(
        f"Colunas antes: "
        f"{len(df_antes.columns)}"
    )

    print(
        f"Colunas depois: "
        f"{len(df_depois.columns)}"
    )

    print()

    if not logs:

        print(
            "Nenhum enriquecimento "
            "foi realizado."
        )

        return

    for log in logs:

        modulo = log.get(
            "modulo",
            "desconhecido"
        )

        status = log.get(
            "status",
            "desconhecido"
        )

        print(
            f"[{status.upper()}] "
            f"{modulo.upper()}"
        )

        if status == "sucesso":

            if "tabela" in log:

                print(
                    f"  Tabela utilizada: "
                    f"{log['tabela']}"
                )

            if (
                "produtos_analisados"
                in log
            ):

                print(
                    f"  Produtos analisados: "
                    f"{log['produtos_analisados']}"
                )

            if (
                "registros_avaliacao_validos"
                in log
            ):

                print(
                    f"  Avaliações válidas: "
                    f"{log['registros_avaliacao_validos']}"
                )

            if (
                "registros_ignorados"
                in log
            ):

                print(
                    f"  Registros ignorados: "
                    f"{log['registros_ignorados']}"
                )

            if (
                "produtos_sem_devolucao"
                in log
            ):

                print(
                    f"  Produtos sem devolução: "
                    f"{log['produtos_sem_devolucao']}"
                )

            if (
                "colunas_adicionadas"
                in log
            ):

                print(
                    "  Colunas adicionadas:"
                )

                for coluna in (
                    log[
                        "colunas_adicionadas"
                    ]
                ):

                    print(
                        f"  - {coluna}"
                    )

        else:

            print(
                f"  Motivo: "
                f"{log.get('motivo')}"
            )

        print()

    if len(df_antes) == len(df_depois):

        print(
            "Validação de linhas: OK"
        )

        print(
            "O enriquecimento não alterou "
            "a quantidade de registros."
        )

    else:

        print(
            "ATENÇÃO: a quantidade de linhas "
            "foi alterada."
        )


# =========================================================
# PIPELINE ANALÍTICO
# =========================================================


def executar_pipeline_analitico(
    df,
    origem: str,
    diretorio_saida: Path = ROOT,
    arquivos_analisados: list | None = None
):

    print(
        "\n=== INICIANDO PIPELINE ANALÍTICO ===\n"
    )

    print(
        f"Origem dos dados: "
        f"{origem}"
    )

    print(
        f"Linhas: {len(df)} | "
        f"Colunas: {len(df.columns)}"
    )

    # ========================================
    # 1. DIAGNÓSTICO
    # ========================================

    diagnostico = gerar_diagnostico(
        df
    )
    if arquivos_analisados is None:
        arquivos_analisados = [{'nome': origem, 'linhas': len(df), 'colunas': len(df.columns)}]

    print(
        "\n=== DIAGNÓSTICO DOS DADOS ===\n"
    )

    pprint(
        diagnostico
    )

    # ========================================
    # 2. PROBLEMAS
    # ========================================

    problemas = gerar_problemas(
        df,
        diagnostico
    )

    print(
        "\n=== PROBLEMAS ENCONTRADOS ===\n"
    )

    if not problemas:

        print(
            "Nenhum problema encontrado."
        )

    else:

        for problema in problemas:

            print(
                f"- "
                f"[{problema['severidade'].upper()}] "
                f"{problema['mensagem']}"
            )

    # ========================================
    # 3. SALVAR DIAGNÓSTICO
    # ========================================

    salvar_relatorio(
        diagnostico,
        problemas,
        caminho_saida=diretorio_saida / "reports/diagnostico.json"
    )

    print(
        "\nRelatório de diagnóstico salvo em "
        "reports/diagnostico.json"
    )

    # ========================================
    # 4. ETL
    # ========================================

    print(
        "\n=== INICIANDO ETL ===\n"
    )

    df_tratado, logs_etl = executar_etl(
        df,
        diagnostico
    )

    print(
        "=== TRANSFORMAÇÕES REALIZADAS ===\n"
    )

    if not logs_etl:

        print(
            "Nenhuma transformação realizada."
        )

    else:

        for item in logs_etl:

            print(
                f"- {item['coluna']}: "
                f"{item['antes']} -> "
                f"{item['depois']}"
            )

            print(
                f"  Tipo: "
                f"{item['tipo_transformacao']}"
            )

            print(
                f"  {item['detalhes']}\n"
            )

    # ========================================
    # 5. TIPOS APÓS ETL
    # ========================================

    print(
        "\n=== TIPOS APÓS ETL ===\n"
    )

    print(
        df_tratado.dtypes
    )

    # ========================================
    # 6. DIAGNÓSTICO APÓS ETL
    # ========================================

    diagnostico_pos_etl = gerar_diagnostico(
        df_tratado
    )

    print(
        "\n=== DIAGNÓSTICO APÓS ETL ===\n"
    )

    print(
        "Valores nulos restantes:"
    )

    encontrou_nulos = False

    for coluna, quantidade in (
        diagnostico_pos_etl[
            "valores_nulos"
        ].items()
    ):

        if quantidade > 0:

            encontrou_nulos = True

            print(
                f"- {coluna}: "
                f"{quantidade}"
            )

    if not encontrou_nulos:

        print(
            "- Nenhum valor nulo restante."
        )

    print(
        "\nLinhas duplicadas:",
        diagnostico_pos_etl[
            "linhas_duplicadas"
        ]
    )

    # ========================================
    # 7. RESUMO ETL
    # ========================================

    nulos_antes = sum(
        diagnostico[
            "valores_nulos"
        ].values()
    )

    nulos_depois = sum(
        diagnostico_pos_etl[
            "valores_nulos"
        ].values()
    )

    nulos_tratados = (
        nulos_antes
        - nulos_depois
    )

    print(
        "\n=== RESUMO DO ETL ===\n"
    )

    print(
        f"Nulos antes: "
        f"{nulos_antes}"
    )

    print(
        f"Nulos depois: "
        f"{nulos_depois}"
    )

    print(
        f"Nulos tratados: "
        f"{nulos_tratados}"
    )

    print(
        "Duplicados antes:",
        diagnostico[
            "linhas_duplicadas"
        ]
    )

    print(
        "Duplicados depois:",
        diagnostico_pos_etl[
            "linhas_duplicadas"
        ]
    )

    # ========================================
    # 8. SALVAR BASE TRATADA
    # ========================================

    salvar_dados_tratados(
        df_tratado,
        caminho_saida=diretorio_saida / "data/processed/vendas_tratadas.csv"
    )

    print(
        "\nDados tratados salvos em "
        "data/processed/vendas_tratadas.csv"
    )

    print(
        "\n=== ETL FINALIZADO COM SUCESSO ==="
    )

    # ========================================
    # 9. MÉTRICAS DERIVADAS
    # ========================================

    df_analise, metricas_criadas = (
        criar_metricas_derivadas(
            df_tratado
        )
    )

    print(
        "\n=== MÉTRICAS DERIVADAS ===\n"
    )

    if not metricas_criadas:

        print(
            "Nenhuma métrica derivada "
            "precisou ser criada."
        )

    else:

        for metrica in metricas_criadas:

            print(
                f"- Métrica: "
                f"{metrica['metrica']}"
            )

            print(
                f"  Coluna criada: "
                f"{metrica['coluna_criada']}"
            )

            print(
                f"  Fórmula: "
                f"{metrica['formula']}"
            )

            print(
                f"  Origem: "
                f"{metrica['origem']}\n"
            )

    # ========================================
    # 10. MAPEAMENTO
    # ========================================

    mapeamento = mapear_colunas(
        df_analise
    )

    print(
        "\n=== MAPEAMENTO DAS COLUNAS ===\n"
    )

    for coluna, dados in (
        mapeamento.items()
    ):

        print(
            f"{coluna}: "
            f"{dados['papel']} | "
            f"{dados['tipo']} | "
            f"{dados['agregacao']} | "
            f"confiança: "
            f"{dados['confianca']}%"
        )

    # ========================================
    # 11. KPIS
    # ========================================

    kpis = calcular_kpis(
        df_analise
    )

    print(
        "\n=== KPIS DE NEGÓCIO ===\n"
    )

    if not kpis:

        print(
            "Nenhum KPI pôde ser calculado."
        )

    else:

        for nome, valor in (
            kpis.items()
        ):

            print(
                f"{nome}: {valor}"
            )

    # ========================================
    # 12. ANÁLISE TEMPORAL
    # ========================================

    analise_mensal = analisar_meses(
        df_analise
    )

    print(
        "\n=== ANÁLISE MENSAL ===\n"
    )

    if "erro" in analise_mensal:

        print(
            analise_mensal["erro"]
        )

    else:

        melhor_mes = (
            analise_mensal[
                "melhor_mes"
            ]
        )

        pior_mes = (
            analise_mensal[
                "pior_mes"
            ]
        )

        print(
            f"Melhor mês: "
            f"{melhor_mes['periodo']} | "
            f"Faturamento: "
            f"{melhor_mes['faturamento']}"
        )

        print(
            f"Pior mês: "
            f"{pior_mes['periodo']} | "
            f"Faturamento: "
            f"{pior_mes['faturamento']}"
        )

        print(
            "\nFaturamento por mês:"
        )

        for periodo, valor in (
            analise_mensal[
                "faturamento_mensal"
            ].items()
        ):

            print(
                f"- {periodo}: "
                f"{valor}"
            )

        print(
            "\nVariação mensal:"
        )

        for periodo, variacao in (
            analise_mensal[
                "variacao_mensal"
            ].items()
        ):

            print(
                f"- {periodo}: "
                f"{variacao}%"
            )

        print(
            "\nPeríodos que precisam "
            "de revisão:"
        )

        periodos_suspeitos = (
            analise_mensal[
                "periodos_suspeitos"
            ]
        )

        if not periodos_suspeitos:

            print(
                "- Nenhum período "
                "suspeito encontrado."
            )

        else:

            for periodo in (
                periodos_suspeitos
            ):

                print(
                    f"- "
                    f"{periodo['periodo']} | "
                    f"Registros: "
                    f"{periodo['registros']} | "
                    f"Faturamento: "
                    f"{periodo['faturamento']}"
                )

    # ========================================
    # 13. CLIENTES
    # ========================================

    analise_clientes = analisar_clientes(
        df_analise
    )

    print(
        "\n=== ANÁLISE DE CLIENTES ===\n"
    )

    if "erro" in analise_clientes:

        print(
            analise_clientes["erro"]
        )

    else:

        if (
            "quantidade_clientes"
            in analise_clientes
        ):

            print(
                "Quantidade de clientes: "
                f"{analise_clientes['quantidade_clientes']}"
            )

        if (
            "maior_faturamento"
            in analise_clientes
        ):

            cliente = (
                analise_clientes[
                    "maior_faturamento"
                ]
            )

            print(
                "\nCliente com maior faturamento:"
            )

            print(
                f"- "
                f"{cliente['cliente']} | "
                f"Faturamento: "
                f"{cliente['faturamento']}"
            )

        if (
            "top_5_faturamento"
            in analise_clientes
        ):

            print(
                "\nTop 5 clientes "
                "por faturamento:"
            )

            for cliente in (
                analise_clientes[
                    "top_5_faturamento"
                ]
            ):

                print(
                    f"- "
                    f"{cliente['cliente']} | "
                    f"Faturamento: "
                    f"{cliente['faturamento']}"
                )

        if (
            "concentracao_top_5"
            in analise_clientes
        ):

            print(
                "\nConcentração de faturamento "
                "nos 5 maiores clientes:"
            )

            print(
                f"- "
                f"{analise_clientes['concentracao_top_5']}%"
            )

        if (
            "maior_lucro"
            in analise_clientes
        ):

            cliente = (
                analise_clientes[
                    "maior_lucro"
                ]
            )

            print(
                "\nCliente com maior lucro:"
            )

            print(
                f"- "
                f"{cliente['cliente']} | "
                f"Lucro: "
                f"{cliente['lucro']}"
            )

        if (
            "clientes_com_prejuizo"
            in analise_clientes
        ):

            clientes_prejuizo = (
                analise_clientes[
                    "clientes_com_prejuizo"
                ]
            )

            print(
                "\nClientes com prejuízo:"
            )

            if not clientes_prejuizo:

                print(
                    "- Nenhum cliente com "
                    "lucro negativo encontrado."
                )

            else:

                for cliente in (
                    clientes_prejuizo
                ):

                    print(
                        f"- "
                        f"{cliente['cliente']} | "
                        f"Lucro: "
                        f"{cliente['lucro']}"
                    )

    # ========================================
    # 14. DESEMPENHO
    # ========================================

    desempenho = analisar_desempenho(
        df_analise
    )

    print(
        "\n=== ANÁLISE DE DESEMPENHO ===\n"
    )

    if "erro" in desempenho:

        print(
            desempenho["erro"]
        )

    else:

        print(
            f"Lucro total: "
            f"{desempenho['lucro_total']}"
        )

        print(
            "Registros com prejuízo: "
            f"{desempenho['quantidade_registros_prejuizo']}"
        )

        print(
            f"Prejuízo total: "
            f"{desempenho['prejuizo_total']}"
        )

        if (
            "melhor_periodo_lucro"
            in desempenho
        ):

            melhor = (
                desempenho[
                    "melhor_periodo_lucro"
                ]
            )

            print(
                "\nMelhor período de lucro:"
            )

            print(
                f"- "
                f"{melhor['periodo']} | "
                f"Lucro: "
                f"{melhor['lucro']}"
            )

        if (
            "pior_periodo_lucro"
            in desempenho
        ):

            pior = (
                desempenho[
                    "pior_periodo_lucro"
                ]
            )

            print(
                "\nPior período de lucro:"
            )

            print(
                f"- "
                f"{pior['periodo']} | "
                f"Lucro: "
                f"{pior['lucro']}"
            )

        if (
            "periodos_com_prejuizo"
            in desempenho
        ):

            periodos_prejuizo = (
                desempenho[
                    "periodos_com_prejuizo"
                ]
            )

            print(
                "\nPeríodos com prejuízo:"
            )

            if not periodos_prejuizo:

                print(
                    "- Nenhum período mensal "
                    "com lucro negativo."
                )

            else:

                for periodo in (
                    periodos_prejuizo
                ):

                    print(
                        f"- "
                        f"{periodo['periodo']} | "
                        f"Lucro: "
                        f"{periodo['lucro']}"
                    )

    # ========================================
    # 15. CRESCIMENTO
    # ========================================

    crescimento = analisar_crescimento(
        df_analise
    )

    print(
        "\n=== ANÁLISE DE CRESCIMENTO ===\n"
    )

    if "erro" in crescimento:

        print(
            crescimento["erro"]
        )

    else:

        faturamento = (
            crescimento[
                "faturamento"
            ]
        )

        print(
            "Faturamento:"
        )

        print(
            f"- Tendência: "
            f"{faturamento['tendencia']}"
        )

        print(
            f"- Evolução total: "
            f"{faturamento['evolucao_total']}%"
        )

        if (
            "maior_crescimento"
            in faturamento
        ):

            maior = (
                faturamento[
                    "maior_crescimento"
                ]
            )

            print(
                "\nMaior crescimento "
                "de faturamento:"
            )

            print(
                f"- "
                f"{maior['periodo']} | "
                f"{maior['variacao']}%"
            )

        if (
            "maior_queda"
            in faturamento
        ):

            queda = (
                faturamento[
                    "maior_queda"
                ]
            )

            print(
                "\nMaior queda "
                "de faturamento:"
            )

            print(
                f"- "
                f"{queda['periodo']} | "
                f"{queda['variacao']}%"
            )

        print(
            "\nSequências de queda "
            "no faturamento:"
        )

        sequencias = faturamento.get(
            "sequencias_queda",
            []
        )

        if not sequencias:

            print(
                "- Nenhuma sequência "
                "de quedas encontrada."
            )

        else:

            for sequencia in sequencias:

                periodos = [
                    item["periodo"]
                    for item in sequencia
                ]

                print(
                    "- "
                    + " -> ".join(
                        periodos
                    )
                )

        if "lucro" in crescimento:

            lucro = (
                crescimento[
                    "lucro"
                ]
            )

            print(
                "\nLucro:"
            )

            print(
                f"- Tendência: "
                f"{lucro['tendencia']}"
            )

            print(
                f"- Evolução total: "
                f"{lucro['evolucao_total']}%"
            )

    # ========================================
    # 16. DIMENSÕES
    # ========================================

    dimensoes = analisar_dimensoes(
        df_analise
    )

    print(
        "\n=== ANÁLISE DE DIMENSÕES ===\n"
    )

    if not dimensoes:

        print(
            "Nenhuma dimensão adicional "
            "foi identificada para análise."
        )

    else:

        for papel, dados in (
            dimensoes.items()
        ):

            print(
                f"\n--- {papel.upper()} ---"
            )

            print(
                "Coluna identificada: "
                f"{dados['coluna']}"
            )

            print(
                "Quantidade de valores: "
                f"{dados['quantidade_valores']}"
            )

            if (
                "top_faturamento"
                in dados
            ):

                print(
                    "\nTop 5 por faturamento:"
                )

                for item in (
                    dados[
                        "top_faturamento"
                    ]
                ):

                    print(
                        f"- "
                        f"{item['valor']} | "
                        f"Faturamento: "
                        f"{item['faturamento']}"
                    )

            if (
                "participacao_faturamento"
                in dados
            ):

                print(
                    "\nParticipação no faturamento:"
                )

                for item in (
                    dados[
                        "participacao_faturamento"
                    ]
                ):

                    print(
                        f"- "
                        f"{item['valor']} | "
                        f"Participação: "
                        f"{item['participacao']}%"
                    )

            if (
                "mais_vendidos"
                in dados
            ):

                print(
                    "\nTop 5 por volume:"
                )

                for item in (
                    dados[
                        "mais_vendidos"
                    ]
                ):

                    print(
                        f"- "
                        f"{item['valor']} | "
                        f"Quantidade: "
                        f"{item['quantidade']}"
                    )

            if (
                "participacao_volume"
                in dados
            ):

                print(
                    "\nParticipação no volume:"
                )

                for item in (
                    dados[
                        "participacao_volume"
                    ]
                ):

                    print(
                        f"- "
                        f"{item['valor']} | "
                        f"Participação: "
                        f"{item['participacao']}%"
                    )

            if (
                "top_valor_medio_unidade"
                in dados
            ):

                print(
                    "\nTop 5 por valor médio "
                    "por unidade:"
                )

                for item in (
                    dados[
                        "top_valor_medio_unidade"
                    ]
                ):

                    print(
                        f"- "
                        f"{item['valor']} | "
                        f"Valor médio/unidade: "
                        f"{item['valor_medio_unidade']}"
                    )

            if (
                "top_lucro"
                in dados
            ):

                print(
                    "\nTop 5 por lucro:"
                )

                for item in (
                    dados[
                        "top_lucro"
                    ]
                ):

                    print(
                        f"- "
                        f"{item['valor']} | "
                        f"Lucro: "
                        f"{item['lucro']}"
                    )

            if (
                "resultados_negativos"
                in dados
            ):

                negativos = (
                    dados[
                        "resultados_negativos"
                    ]
                )

                print(
                    "\nResultados negativos:"
                )

                if not negativos:

                    print(
                        "- Nenhum resultado "
                        "negativo encontrado."
                    )

                else:

                    for item in negativos:

                        print(
                            f"- "
                            f"{item['valor']} | "
                            f"Lucro: "
                            f"{item['lucro']}"
                        )

    # ========================================
    # 17. PRODUTOS
    # ========================================

    produtos = analisar_produtos(
        df_analise
    )

    print(
        "\n=== ANÁLISE DE PRODUTOS ===\n"
    )

    if "erro" in produtos:

        print(
            produtos["erro"]
        )

    else:

        print(
            f"Coluna de produto: "
            f"{produtos['coluna_produto']}"
        )

        print(
            f"Quantidade de produtos: "
            f"{produtos['quantidade_produtos']}"
        )

        if "mais_vendidos" in produtos:

            print(
                "\nTop 5 produtos mais vendidos:"
            )

            for item in (
                produtos[
                    "mais_vendidos"
                ]
            ):

                print(
                    f"- "
                    f"{item['produto']} | "
                    f"Quantidade: "
                    f"{item['quantidade']}"
                )

        if "top_faturamento" in produtos:

            print(
                "\nTop 5 produtos por faturamento:"
            )

            for item in (
                produtos[
                    "top_faturamento"
                ]
            ):

                print(
                    f"- "
                    f"{item['produto']} | "
                    f"Faturamento: "
                    f"{item['faturamento']}"
                )

        if "top_lucro" in produtos:

            print(
                "\nTop 5 produtos por lucro:"
            )

            for item in (
                produtos[
                    "top_lucro"
                ]
            ):

                print(
                    f"- "
                    f"{item['produto']} | "
                    f"Lucro: "
                    f"{item['lucro']}"
                )

        if (
            "produtos_com_prejuizo"
            in produtos
        ):

            negativos = (
                produtos[
                    "produtos_com_prejuizo"
                ]
            )

            print(
                "\nProdutos com prejuízo:"
            )

            if not negativos:

                print(
                    "- Nenhum produto "
                    "com prejuízo."
                )

            else:

                for item in negativos:

                    print(
                        f"- "
                        f"{item['produto']} | "
                        f"Lucro: "
                        f"{item['lucro']}"
                    )

        if (
            "oportunidades_crescimento"
            in produtos
        ):

            oportunidades_produtos = (
                produtos[
                    "oportunidades_crescimento"
                ]
            )

            print(
                "\nPossíveis produtos "
                "com potencial de crescimento:"
            )

            if not oportunidades_produtos:

                print(
                    "- Nenhuma oportunidade "
                    "identificada."
                )

            else:

                for item in (
                    oportunidades_produtos
                ):

                    print(
                        f"- "
                        f"{item['produto']} | "
                        f"Faturamento: "
                        f"{item['faturamento']} | "
                        f"Lucro: "
                        f"{item['lucro']}"
                    )

    # ========================================
    # 18. OPORTUNIDADES
    # ========================================

    oportunidades = analisar_oportunidades(
        crescimento,
        dimensoes,
        analise_clientes,
        desempenho,
        produtos
    )

    print(
        "\n=== OPORTUNIDADES E PONTOS "
        "DE ATENÇÃO ===\n"
    )

    if not oportunidades:

        print(
            "Nenhuma oportunidade ou ponto "
            "de atenção relevante encontrado."
        )

    else:

        for oportunidade in oportunidades:

            print(
                f"[{oportunidade['tipo'].upper()}] "
                f"[{oportunidade['prioridade'].upper()}] "
                f"[{oportunidade['categoria'].upper()}]"
            )

            print(
                oportunidade[
                    "mensagem"
                ]
            )

            print()

    # ========================================
    # 19. INSIGHTS
    # ========================================

    insights = gerar_insights(
        kpis,
        analise_mensal,
        analise_clientes,
        desempenho,
        crescimento,
        dimensoes,
        produtos,
        oportunidades
    )

    print(
        "\n=== INSIGHTS AUTOMÁTICOS ===\n"
    )

    if not insights:

        print(
            "Nenhum insight relevante encontrado."
        )

    else:

        for insight in insights:

            print(
                f"[{insight['tipo'].upper()}] "
                f"[{insight['prioridade'].upper()}] "
                f"[{insight['categoria'].upper()}]"
            )

            print(
                insight[
                    "mensagem"
                ]
            )

            print()

    # ========================================
    # 20. RESUMO EXECUTIVO - V0.6
    # ========================================

    resumo_executivo = (
        gerar_resumo_executivo(
            kpis,
            analise_mensal,
            analise_clientes,
            desempenho,
            crescimento,
            produtos,
            oportunidades,
            insights
        )
    )

    resumo_executivo['dados'] = gerar_qualidade_dados(
        diagnostico, problemas, logs_etl, arquivos_analisados
    )
    print(
        "\n=== RESUMO EXECUTIVO ===\n"
    )

    status_geral = (
        resumo_executivo.get(
            "status_geral",
            {}
        )
    )

    print(
        f"Status geral: "
        f"{status_geral.get('status', 'indefinido')}"
    )

    print(
        f"Score: "
        f"{status_geral.get('score', 0)}"
    )

    motivos_status = (
        status_geral.get(
            "motivos",
            []
        )
    )

    if motivos_status:

        print(
            "\nPrincipais motivos:"
        )

        for motivo in motivos_status:

            print(
                f"- {motivo}"
            )

    # ========================================
    # KPIS DO RESUMO
    # ========================================

    resumo_kpis = (
        resumo_executivo.get(
            "kpis",
            {}
        )
    )

    if resumo_kpis:

        print(
            "\nKPIs principais:"
        )

        for nome, valor in (
            resumo_kpis.items()
        ):

            if valor is not None:

                print(
                    f"- {nome}: "
                    f"{valor}"
                )

    # ========================================
    # RISCOS PRINCIPAIS
    # ========================================

    riscos = (
        resumo_executivo.get(
            "principais_riscos",
            []
        )
    )

    if riscos:

        print(
            "\nPrincipais riscos:"
        )

        for risco in riscos:

            print(
                f"- "
                f"[{str(risco.get('prioridade', '')).upper()}] "
                f"[{str(risco.get('categoria', '')).upper()}] "
                f"{risco.get('mensagem')}"
            )

    # ========================================
    # OPORTUNIDADES PRINCIPAIS
    # ========================================

    oportunidades_resumo = (
        resumo_executivo.get(
            "oportunidades",
            []
        )
    )

    if oportunidades_resumo:

        print(
            "\nPrincipais oportunidades:"
        )

        for oportunidade in (
            oportunidades_resumo
        ):

            print(
                f"- "
                f"[{str(oportunidade.get('categoria', '')).upper()}] "
                f"{oportunidade.get('mensagem')}"
            )

    # ========================================
    # 21. SALVAR RESUMO EXECUTIVO JSON
    # ========================================

    caminho_resumo = (
        salvar_resumo_executivo(
            resumo_executivo,
            caminho=diretorio_saida / "reports/resumo_executivo.json"
        )
    )

    print(
        "\nResumo executivo salvo em "
        f"{caminho_resumo}"
    )

    # ========================================
    # 22. SALVAR ANÁLISE COMPLETA
    # ========================================

    salvar_analise(
        kpis,
        analise_mensal,
        analise_clientes,
        desempenho,
        crescimento,
        dimensoes,
        produtos,
        oportunidades,
        insights,
        caminho_saida=diretorio_saida / "reports/analise.json"
    )

    print(
        "\nRelatório de análise salvo em "
        "reports/analise.json"
    )

    # ========================================
    # 23. FINALIZAÇÃO
    # ========================================

    print(
        "\n=== DATAAGENT FINALIZADO "
        "COM SUCESSO ==="
    )


    return resumo_executivo

# =========================================================
# MAIN
# =========================================================


def executar_dataagent(diretorio_dados=ROOT / "data/samples", diretorio_saida=ROOT, estrito=False):
    """Pipeline compartilhado por CLI e API; não captura stdout para retornar dados."""
    # Preserva os logs UTF-8 também quando chamado pelo Uvicorn no Windows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    diretorio_dados = Path(diretorio_dados)
    diretorio_saida = Path(diretorio_saida)

    try:

        # ========================================
        # 1. DETECTAR ARQUIVOS
        # ========================================

        arquivos = encontrar_arquivos(diretorio_dados)

        quantidade_arquivos = len(
            arquivos
        )

        print(
            "\n=== DETECÇÃO DE DADOS ===\n"
        )

        print(
            f"Arquivos encontrados: "
            f"{quantidade_arquivos}"
        )

        # ========================================
        # 2. ARQUIVO ÚNICO
        # ========================================

        if quantidade_arquivos == 1:

            print(
                "\n=== MODO ARQUIVO ÚNICO ===\n"
            )

            print(
                f"Arquivo detectado: "
                f"{arquivos[0].name}"
            )

            try:
                df = carregar_dados(arquivos[0])
            except Exception as erro:
                raise ValueError("Não foi possível ler o arquivo enviado.") from erro
            if df.empty:
                raise ValueError("O arquivo não contém linhas de dados.")

            return executar_pipeline_analitico(
                df,
                origem=arquivos[0].name,
                diretorio_saida=diretorio_saida
            )

        # ========================================
        # 3. MÚLTIPLAS TABELAS
        # ========================================

        print(
            "\n=== MODO MÚLTIPLAS TABELAS ==="
        )

        print(
            "\nArquivos detectados:"
        )

        for arquivo in arquivos:

            print(
                f"- {arquivo.name}"
            )

        # ========================================
        # 4. CARREGAR TABELAS
        # ========================================

        tabelas = (
            carregar_multiplas_tabelas(diretorio_dados, estrito=estrito)
        )

        exibir_resumo_tabelas(
            tabelas
        )

        print(
            "\n=== CARREGAMENTO MÚLTIPLO "
            "FINALIZADO ===\n"
        )

        print(
            "Todas as tabelas foram "
            "carregadas com sucesso."
        )

        # ========================================
        # 5. DETECTAR RELACIONAMENTOS
        # ========================================

        print(
            "\n=== ANALISANDO RELACIONAMENTOS ==="
        )

        relacionamentos = (
            detectar_relacionamentos(
                tabelas
            )
        )

        exibir_relacionamentos(
            relacionamentos
        )

        if not relacionamentos:

            print(
                "\nNão foi possível construir "
                "um dataset analítico porque "
                "nenhum relacionamento confiável "
                "foi identificado."
            )

            raise ValueError("Nenhum relacionamento confiável foi identificado entre as tabelas.")

        # ========================================
        # 6. CRIAR DATASET ANALÍTICO
        # ========================================

        print(
            "\n=== CRIANDO DATASET "
            "ANALÍTICO ==="
        )

        (
            df_analitico,
            tabela_principal,
            logs_merge
        ) = criar_dataset_analitico(
            tabelas,
            relacionamentos
        )

        exibir_logs_merge(
            tabela_principal,
            df_analitico,
            logs_merge
        )

        # ========================================
        # 7. ENRIQUECER DATASET
        # ========================================

        df_antes_enriquecimento = (
            df_analitico.copy()
        )

        (
            df_enriquecido,
            logs_enriquecimento
        ) = enriquecer_dataset(
            df_analitico,
            tabelas
        )

        exibir_logs_enriquecimento(
            df_antes_enriquecimento,
            df_enriquecido,
            logs_enriquecimento
        )

        # ========================================
        # 8. COLUNAS RESULTANTES
        # ========================================

        print(
            "\n=== COLUNAS DO DATASET "
            "ENRIQUECIDO ===\n"
        )

        for coluna in (
            df_enriquecido.columns
        ):

            print(
                f"- {coluna}"
            )

        # ========================================
        # 9. PIPELINE ANALÍTICO
        # ========================================

        df_enriquecido.attrs['ingestao'] = {
            nome: tabela.attrs['ingestao']
            for nome, tabela in tabelas.items() if 'ingestao' in tabela.attrs
        }
        return executar_pipeline_analitico(
            df_enriquecido,
            arquivos_analisados=[
                {'nome': tabela.attrs.get('ingestao', {}).get('arquivo', nome),
                 'linhas': len(tabela), 'colunas': len(tabela.columns)}
                for nome, tabela in tabelas.items()
            ],
            origem=(
                "Dataset multitabelas "
                "enriquecido baseado em "
                f"{tabela_principal}"
            ),
            diretorio_saida=diretorio_saida
        )

    except FileNotFoundError as erro:

        if estrito:
            raise

        print(
            f"\nErro ao localizar arquivo: "
            f"{erro}"
        )

    except ValueError as erro:

        if estrito:
            raise

        print(
            f"\nErro nos dados: "
            f"{erro}"
        )

    except Exception as erro:

        if estrito:
            raise

        print(
            f"\nErro inesperado: "
            f"{erro}"
        )


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return executar_dataagent()


if __name__ == "__main__":
    main()
