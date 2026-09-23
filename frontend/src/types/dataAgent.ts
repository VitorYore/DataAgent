// Nomes e valores preservam o contrato fornecido pelo backend.
// Classificações são strings porque seus valores possíveis não foram especificados.
export interface GeneralStatus {
  score: number | null
  status: string | null
  motivos: string[]
}

export interface Kpis {
  faturamento_total: number | null
  lucro_total: number | null
  custo_total: number | null
  margem_lucro: number | null
  ticket_medio: number | null
  quantidade_pedidos: number | null
  quantidade_vendida: number | null
  quantidade_registros?: number | null
  valor_total?: number | null
  valor_com_desconto?: number | null
  margem_bruta?: number | null
  margem_bruta_percentual?: number | null
  margem_bruta_percentual_metodo?: string | null
}

export interface TemporalPoint {
  periodo: string
  faturamento?: number | null
  lucro?: number | null
  metrica_valor?: number | null
  nome_metrica?: string | null
}

export interface ProductRankingItem {
  posicao: number | null
  produto: string | null
  produto_id: number | string | null
  quantidade: number | null
  faturamento: number | null
  lucro: number | null
  avaliacao_media: number | null
  estoque_atual: number | null
  taxa_devolucao: number | null
}

export interface TemporalAnalysis {
  periodo_analitico?: { inicio: string; fim: string }
  anomalias_temporais?: {
    quantidade: number
    confianca: number
    periodo_predominante?: { inicio: string; fim: string; ano_inicio?: number; ano_fim?: number } | null
    datas_exemplos?: string[]
    anos_anomalos?: number[]
  }
  serie_temporal?: TemporalPoint[]
  metrica_principal?: string | null
  nome_metrica_principal?: string | null
  tendencia_metrica?: string | null
  evolucao_metrica?: number | null
  evolucao_motivo?: 'base_zero' | 'base_muito_baixa' | 'mudanca_de_sinal' | 'dados_insuficientes' | null
  evolucao_variacao_absoluta?: number | null
  periodo_evolucao?: { inicio: string; fim: string; valor_inicial: number; valor_final: number }
  melhor_periodo?: { periodo: string; faturamento?: number | null; valor?: number | null; nome_metrica?: string }
  pior_periodo?: { periodo: string; faturamento?: number | null; valor?: number | null; nome_metrica?: string }
  tendencia_faturamento?: string
  evolucao_faturamento?: number | null
  maior_crescimento?: { periodo: string; variacao: number | null }
  maior_queda?: { periodo: string; variacao: number | null }
}

export interface CustomerRankingItem {
  posicao: number
  cliente: string
  cliente_id?: string | number | null
  faturamento?: number | null
  lucro?: number | null
}

export interface CustomerSummary {
  metrica_principal?: { conceito: string; label: string; coluna?: string } | null
  participacao_maior_cliente_metrica?: { conceito: string; label: string } | null
  concentracao_top_5_metrica?: { conceito: string; label: string } | null
  rankings?: Record<string, { conceito: string; label: string; items: { posicao: number; cliente: string; cliente_id?: string | null; valor: number; conceito: string }[] }>
  maior_valor_total?: { cliente: string; valor_total: number | null }
  maior_valor_com_desconto?: { cliente: string; valor_com_desconto: number | null }
  maior_margem_bruta?: { cliente: string; margem_bruta: number | null }
  cliente_maior_margem_bruta?: { cliente: string; margem_bruta: number | null }
  clientes_metrica_negativa?: { conceito: string; label: string; quantidade: number }
  clientes_margem_bruta_negativa?: number | null
  participacao_maior_cliente?: number | null
  clientes_resultado_negativo?: number | null
  ranking_faturamento?: CustomerRankingItem[]
  ranking_lucro?: CustomerRankingItem[]
  insights_clientes?: string[]
  quantidade_clientes?: number | null
  cliente_maior_faturamento?: { cliente: string; faturamento: number | null }
  cliente_maior_lucro?: { cliente: string; lucro: number | null }
  concentracao_top_5?: number | null
  cliente_maior_valor_total?: { cliente: string; valor_total: number | null }
  cliente_maior_valor_com_desconto?: { cliente: string; valor_com_desconto: number | null }
  ranking_valor_total?: { posicao: number; cliente: string; cliente_id?: string | number | null; valor_total: number | null }[]
}

export interface ProductSummary {
  ranking_produtos?: ProductRankingItem[]
  quantidade_produtos?: number | null
  produto_mais_vendido?: { produto: string; quantidade: number | null }
  produto_maior_faturamento?: { produto: string; faturamento: number | null }
  produto_maior_lucro?: { produto: string; lucro: number | null }
  produtos_risco_ruptura?: number | null
  produtos_estoque_excessivo?: number | null
}

export interface Risk {
  categoria: string
  prioridade: string
  mensagem: string
}

export interface Opportunity {
  categoria: string
  prioridade: string
  mensagem: string
}

export interface Insight {
  tipo: string
  categoria: string
  prioridade: string
  mensagem: string
}

export interface ExecutiveSummary {
  analysis_id?: string | null
  suficiencia_analitica?: 'suficiente' | 'insuficiente' | 'aguardando_mapeamento' | string
  dados?: DataQuality | null
  status_geral: GeneralStatus
  kpis: Kpis
  temporal: TemporalAnalysis
  clientes: CustomerSummary
  produtos: ProductSummary
  principais_riscos: Risk[]
  oportunidades: Opportunity[]
  principais_insights: Insight[]
}

export interface SemanticColumnProfile {
  nome: string
  papel_estrutural: string
  confianca_estrutural: number
  conceito_semantico: string | null
  confianca_semantica: number
  estado: 'confirmado' | 'provavel' | 'desconhecido'
  exemplos: string[]
  percentual_nulos: number
  cardinalidade: number
  mapeamento_relevante?: boolean
  conceitos_compativeis: string[]
  sugestao_semantica?: string | null
  origem_mapeamento?: string | null
  confianca_mapeamento?: number | null
}

export interface SemanticMappingRequest {
  status: 'mapping_required'
  analysis_id: string
  message: string
  detected_columns: SemanticColumnProfile[]
  automatic_mappings: Record<string, string>
  required_mappings: { coluna: string; conceitos_compativeis: string[] }[]
  concepts: { id: string; label: string }[]
}

export type AnalysisResponse =
  | { status: 'success'; files_processed: number; summary: ExecutiveSummary }
  | SemanticMappingRequest

export interface AnalysisHistoryItem {
  id: string
  analysis_id?: string
  created_at?: string
  data_analise?: string
  arquivos?: string[]
  mode?: 'single' | 'multi' | string
  status?: string | null
  analysis_status?: string
  dataset?: { rows?: number | null; columns?: number | null }
  period?: { start?: string | null; end?: string | null }
  available_metrics?: string[]
  available_dimensions?: string[]
  quality?: Record<string, number | string | null>
  semantic_mapping_summary?: DataQuality['mapeamento_semantico']
  report_available?: boolean
  kpis?: Partial<Kpis>
  score?: number | null
  status_negocio?: string | null
}

export interface ComparisonMetric {
  concept?: string
  label?: string
  left?: number | null
  right?: number | null
  absolute_change?: number | null
  percentage_change?: number | null
  percentage_point_change?: number | null
  direction?: 'increase' | 'decrease' | 'stable' | string
  atual?: number | null
  anterior?: number | null
  variacao_percentual?: number | null
  variacao_pontos_percentuais?: number | null
}

export interface AnalysisComparison {
  status: 'insuficiente' | 'disponivel' | 'available'
  mensagem?: string
  left_analysis?: string
  right_analysis?: string
  analyses?: { left: AnalysisHistoryItem; right: AnalysisHistoryItem }
  periods?: { left: { start?: string | null; end?: string | null }; right: { start?: string | null; end?: string | null } }
  period_comparability?: 'same_duration' | 'similar_duration' | 'different_duration' | 'unknown'
  metrics?: Partial<Record<string, ComparisonMetric>>
  dimensions?: Record<string, { metric: string; common: { id: string; label: string; left: number; right: number; absolute_change: number; identity_reliable: boolean }[]; only_left: { id: string; label: string; value: number }[]; only_right: { id: string; label: string; value: number }[]; identity_reliability: string }>
  temporal?: { concept: string; label?: string; left_range: { start?: string | null; end?: string | null }; right_range: { start?: string | null; end?: string | null }; shared_periods: { period: string; left: number; right: number }[] } | null
  quality?: Record<string, { left: number; right: number; absolute_change: number }>
  insights?: { category: string; type: string; priority: string; text: string }[]
  analise_atual?: string
  analise_anterior?: string
  metricas: Partial<Record<keyof Kpis, ComparisonMetric>>
}

export interface DataFileInfo {
  nome: string
  linhas?: number | null
  colunas?: number | null
}
export interface DataIssue {
  mensagem: string
  nivel?: string
  severidade?: string
  coluna?: string
  tipo?: string
}
export interface DataTransformation {
  tipo?: string
  coluna?: string
  antes?: string | null
  depois?: string | null
  descricao?: string
}
export interface IngestionInfo {
  arquivo?: string
  aba?: string
  normalizacao?: {
    estrutura_detectada?: string
    confianca_estrutural?: number
    linhas_originais?: number
    registros_extraidos?: number
    linhas_resumo?: number
    linhas_periodo?: number
    linhas_desconhecidas?: number
    linhas_separadas?: number
    quantidade_blocos?: number
    percentual_linhas_reconhecidas?: number
    percentual_linhas_desconhecidas?: number
    revisao_necessaria?: boolean
    status?: 'accepted' | 'partial' | 'review_required'
    confidence_transaction_structure?: number
    confidence_file?: number
    coverage_transaction_rows?: number
    linhas_nao_transacionais_reconhecidas?: number
    unknown_regions?: { inicio: number; fim: number; quantidade: number; exemplos?: unknown[][] }[]
    blocos_detectados?: { start_row: number; end_row: number; classification: string; transaction_rows: number; coverage: number; confidence: number; dominant_signature: string[] }[]
  }
  cabecalho_detectado?: boolean
  linha_cabecalho?: number | null
  confianca_cabecalho?: number | null
  linhas_vazias_removidas?: number
  colunas_vazias_removidas?: number
  colunas_renomeadas?: { posicao: number; original: string; novo: string }[]
  colunas_muitos_nulos?: Record<string, number>
}
export interface DataQuality {
  entity_resolution?: EntityResolution
  arquivos?: DataFileInfo[]
  quantidade_arquivos?: number | null
  status?: string
  escopo?: string
  quantidade_linhas?: number | null
  quantidade_colunas?: number | null
  linhas_duplicadas?: number | null
  total_valores_nulos?: number | null
  percentual_nulos_geral?: number | null
  anomalias_temporais?: TemporalAnalysis['anomalias_temporais']
  coerencia_metricas?: {
    status: 'coerente' | 'inconsistente' | 'insuficiente' | string
    faturamento?: { coluna: string; linhas_validas: number; nulos: number; soma: number | null }
    custo?: { coluna: string; linhas_validas: number; nulos: number; soma: number | null }
    lucro?: { coluna: string; linhas_validas: number; nulos: number; soma: number | null }
    linhas_com_tres_metricas: number
    linhas_reconciliadas: number
    linhas_nao_reconciliadas?: number
    percentual_reconciliado: number | null
    somas_linhas_com_tres_metricas?: Record<string, number>
    residuo_total?: number | null
    limite_percentual_reconciliado?: number
    tolerancia: number
    erro_absoluto_medio?: number | null
    erro_mediano_absoluto?: number | null
    residuo_mediano?: number | null
  } | null
  quantidade_problemas?: number | null
  score_qualidade?: number | null
  classificacao_qualidade?: string | null
  problemas?: (DataIssue | string)[]
  transformacoes?: DataTransformation[]
  mapeamento_semantico?: {
    automatico?: Record<string, string>
    confirmado_pelo_usuario?: Record<string, string>
    origens?: Record<string, { origem?: string; confianca?: number | null }>
  }
  ingestao?: IngestionInfo | Record<string, IngestionInfo>
}

export interface EntitySide { value: string; records: number; orders: number | null; metric_value: number | null }
export interface EntityCandidate {
  entity_type: string; column: string
  candidate_id?: string
  status?: 'pending' | 'merged' | 'kept_separate'
  recommended_value?: string
  canonical_value?: string | null
  left: EntitySide; right: EntitySide
  metric: { concept: string; label: string; column: string } | null
  combined_preview: number | null
  similarity: number; confidence: 'alta' | 'media'; reasons: string[]
}
export interface EntityDecision {
  candidate_id: string; entity_type: string; column: string
  left: string; right: string
  decision: 'merge' | 'keep_separate'
  canonical_value: string | null
  created_at: string; origin: 'user_confirmation'
}
export interface EntityResolution {
  can_decide?: boolean
  decisions?: EntityDecision[]
  summary?: Record<string, { total: number; pending: number; merged: number; kept_separate: number }>
  candidates: EntityCandidate[]
  total_candidates: number
  possible_duplicate_entities: Record<string, number>
  truncated: boolean; stable_id_types: string[]
}
