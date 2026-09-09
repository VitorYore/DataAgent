// Nomes e valores preservam o contrato fornecido pelo backend.
// Classificações são strings porque seus valores possíveis não foram especificados.
export interface GeneralStatus {
  score: number
  status: string
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
}

export interface TemporalPoint {
  periodo: string
  faturamento?: number | null
  lucro?: number | null
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
  serie_temporal?: TemporalPoint[]
  melhor_periodo?: { periodo: string; faturamento: number | null }
  pior_periodo?: { periodo: string; faturamento: number | null }
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
  participacao_maior_cliente?: number | null
  clientes_resultado_negativo?: number | null
  ranking_faturamento?: CustomerRankingItem[]
  ranking_lucro?: CustomerRankingItem[]
  insights_clientes?: string[]
  quantidade_clientes?: number | null
  cliente_maior_faturamento?: { cliente: string; faturamento: number | null }
  cliente_maior_lucro?: { cliente: string; lucro: number | null }
  concentracao_top_5?: number | null
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
  cabecalho_detectado?: boolean
  linha_cabecalho?: number | null
  confianca_cabecalho?: number | null
  linhas_vazias_removidas?: number
  colunas_vazias_removidas?: number
  colunas_renomeadas?: { posicao: number; original: string; novo: string }[]
  colunas_muitos_nulos?: Record<string, number>
}
export interface DataQuality {
  arquivos?: DataFileInfo[]
  quantidade_arquivos?: number | null
  status?: string
  escopo?: string
  quantidade_linhas?: number | null
  quantidade_colunas?: number | null
  linhas_duplicadas?: number | null
  total_valores_nulos?: number | null
  percentual_nulos_geral?: number | null
  quantidade_problemas?: number | null
  score_qualidade?: number | null
  classificacao_qualidade?: string | null
  problemas?: (DataIssue | string)[]
  transformacoes?: DataTransformation[]
  ingestao?: IngestionInfo | Record<string, IngestionInfo>
}
