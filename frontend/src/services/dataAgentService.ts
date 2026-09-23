import type { ExecutiveSummary, AnalysisHistoryItem, AnalysisComparison, AnalysisResponse, SemanticMappingRequest } from '../types/dataAgent'
import { formatPercentage } from '../utils/formatters'

const apiUrl = (import.meta.env.VITE_API_URL?.trim() || 'http://localhost:8000').replace(/\/+$/, '')

const legacyHtmlEntities: Record<string, string> = {
  '&atilde;': '\u00e3', '&iacute;': '\u00ed', '&aacute;': '\u00e1',
  '&eacute;': '\u00e9', '&oacute;': '\u00f3', '&uacute;': '\u00fa',
  '&ccedil;': '\u00e7', '&ecirc;': '\u00ea', '&ocirc;': '\u00f4',
  '&Atilde;': '\u00c3', '&nbsp;': ' ',
}

// Históricos antigos podem conter entidades HTML salvas como texto.
export function normalizeHistoricalText(value: string): string {
  return value.replace(/&(?:atilde|iacute|aacute|eacute|oacute|uacute|ccedil|ecirc|ocirc|Atilde|nbsp);/g, entity => legacyHtmlEntities[entity] ?? entity)
}

function normalizeHistoryItem(item: AnalysisHistoryItem): AnalysisHistoryItem {
  return {
    ...item,
    arquivos: item.arquivos?.map(normalizeHistoricalText),
    status: typeof item.status === 'string' ? normalizeHistoricalText(item.status) : item.status,
    status_negocio: typeof item.status_negocio === 'string' ? normalizeHistoricalText(item.status_negocio) : item.status_negocio,
    quality: item.quality ? {
      ...item.quality,
      classificacao_qualidade: typeof item.quality.classificacao_qualidade === 'string'
        ? normalizeHistoricalText(item.quality.classificacao_qualidade)
        : item.quality.classificacao_qualidade,
    } : item.quality,
  }
}

async function readHistoryResource(path: string): Promise<unknown> {
  const response = await fetch(`${apiUrl}${path}`, { cache: 'no-store', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`Não foi possível carregar o histórico ou a comparação (HTTP ${response.status}).`)
  return response.json()
}

export async function getAnalysisHistory(): Promise<AnalysisHistoryItem[]> {
  const result = await readHistoryResource('/api/analysis/history')
  if (!Array.isArray(result)) throw new Error('A API retornou um histórico inválido.')
  return (result as AnalysisHistoryItem[]).map(normalizeHistoryItem)
}

export async function getAnalysisComparison(): Promise<AnalysisComparison> {
  const result = await readHistoryResource('/api/analysis/compare')
  if (!result || typeof result !== 'object' || !('status' in result) || !['disponivel', 'insuficiente'].includes(String(result.status))) {
    throw new Error('A API retornou uma comparação inválida.')
  }
  return result as AnalysisComparison
}

export async function getExecutiveSummary(): Promise<ExecutiveSummary | null> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/api/analysis/latest`, {
      headers: { Accept: 'application/json' }, cache: 'no-store', signal: AbortSignal.timeout(15000),
    })
  } catch {
    throw new Error(`Não foi possível conectar à API em ${apiUrl}. Verifique se o backend está iniciado e tente novamente.`)
  }
  if (response.status === 404) return null
  if (!response.ok) throw new Error(`Não foi possível carregar a análise (HTTP ${response.status}).`)
  return validateSummary(await response.json())
}

function validateSummary(data: unknown): ExecutiveSummary {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('A API retornou um resumo inválido.')
  const summary = data as Record<string, unknown>
  for (const key of ['status_geral', 'kpis', 'temporal', 'clientes', 'produtos']) {
    if (!summary[key] || typeof summary[key] !== 'object' || Array.isArray(summary[key])) throw new Error('A API retornou um resumo incompleto.')
  }
  for (const key of ['principais_riscos', 'oportunidades', 'principais_insights']) {
    if (!Array.isArray(summary[key])) throw new Error('A API retornou um resumo incompleto.')
  }
  return data as ExecutiveSummary
}

async function readAnalysisResponse(response: Response): Promise<AnalysisResponse> {
  const text = await response.text()
  let result: unknown
  try { result = JSON.parse(text) } catch { result = null }
  if (!response.ok) {
    if (import.meta.env.DEV) console.warn('API DataAgent: erro HTTP', { url: response.url, status: response.status, statusText: response.statusText, body: text })
    const detail = result && typeof result === 'object' && 'detail' in result ? result.detail : null
    if (response.status === 422 && detail && typeof detail === 'object' && 'mensagem' in detail && typeof detail.mensagem === 'string') {
      const confidence = 'confianca' in detail && typeof detail.confianca === 'number' ? ` Confiança estrutural: ${formatPercentage(detail.confianca)}.` : ''
      const reason = 'motivo' in detail && typeof detail.motivo === 'string' ? ` Motivo: ${detail.motivo}` : ''
      throw new Error(`${detail.mensagem}${confidence}${reason} (HTTP 422)`)
    }
    throw new Error(typeof detail === 'string' ? `${detail} (HTTP ${response.status})` : `Não foi possível analisar os arquivos (HTTP ${response.status}).`)
  }
  if (result && typeof result === 'object' && 'status' in result && result.status === 'mapping_required') {
    const pending = result as SemanticMappingRequest
    if (!pending.analysis_id || !Array.isArray(pending.detected_columns) || !Array.isArray(pending.required_mappings) || !Array.isArray(pending.concepts)) {
      throw new Error('A API retornou um pedido de mapeamento inválido.')
    }
    return pending
  }
  if (result && typeof result === 'object' && 'status' in result && result.status === 'success' && 'summary' in result) {
    const payload = result as Extract<AnalysisResponse, { status: 'success' }>
    return { ...payload, summary: validateSummary(payload.summary) }
  }
  throw new Error('A API retornou uma resposta inválida para a análise.')
}

export async function analyzeFiles(files: File[]): Promise<AnalysisResponse> {
  const body = new FormData()
  files.forEach((file) => body.append('files', file))
  let response: Response
  try {
    response = await fetch(`${apiUrl}/api/analysis`, { method: 'POST', body })
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.warn('POST DataAgent: erro de rede', { url: `${apiUrl}/api/analysis`, error })
    throw new Error('A conexão com o backend foi interrompida. A análise pode ainda estar em execução; tente novamente quando a conexão estiver disponível.')
  }
  return readAnalysisResponse(response)
}

export async function getPendingMapping(analysisId: string): Promise<SemanticMappingRequest> {
  const response = await fetch(`${apiUrl}/api/analysis/${encodeURIComponent(analysisId)}/mapping`, { headers: { Accept: 'application/json' }, cache: 'no-store' })
  const result = await readAnalysisResponse(response)
  if (result.status !== 'mapping_required') throw new Error('A análise não aguarda mapeamento.')
  return result
}

export async function confirmAnalysisMapping(analysisId: string, mappings: Record<string, string>): Promise<AnalysisResponse> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/api/analysis/${encodeURIComponent(analysisId)}/mapping`, {
      method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ mappings }),
    })
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.warn('POST DataAgent mapping: erro de rede', { url: `${apiUrl}/api/analysis/${analysisId}/mapping`, error })
    throw new Error('Não foi possível conectar à API para confirmar os campos.')
  }
  return readAnalysisResponse(response)
}


export async function getAnalysis(analysisId: string): Promise<ExecutiveSummary> {
  const response = await fetch(apiUrl + '/api/analysis/' + encodeURIComponent(analysisId), { cache: 'no-store', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Unable to open historical analysis (HTTP ' + response.status + ').')
  return validateSummary(await response.json())
}

export async function decideEntity(analysisId: string, candidateId: string, decision: 'merge' | 'keep_separate'): Promise<AnalysisResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${encodeURIComponent(analysisId)}/entities`, {
    method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidate_id: candidateId, decision }),
  })
  return readAnalysisResponse(response)
}

export async function compareAnalyses(left: string, right: string): Promise<AnalysisComparison> {
  const query = new URLSearchParams({ left, right })
  const result = await readHistoryResource('/api/analysis/compare?' + query.toString())
  if (!result || typeof result !== 'object' || !('status' in result)) throw new Error('The API returned an invalid comparison.')
  return result as AnalysisComparison
}
