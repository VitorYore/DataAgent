import type { ExecutiveSummary } from '../types/dataAgent'

const apiUrl = (import.meta.env.VITE_API_URL?.trim() || 'http://localhost:8000').replace(/\/+$/, '')

// 404 representa ausência de análise; falhas nunca retornam mocks.
export async function getExecutiveSummary(): Promise<ExecutiveSummary | null> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/api/analysis/latest`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    })
  } catch {
    throw new Error(`Não foi possível conectar à API em ${apiUrl}. Verifique se o backend está iniciado e tente novamente.`)
  }
  if (response.status === 404) return null
  if (!response.ok) throw new Error(`Não foi possível carregar a análise (HTTP ${response.status}).`)
  return validateSummary(await response.json())
}

function validateSummary(data: unknown): ExecutiveSummary {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('A API retornou um resumo inválido.')
  }
  const summary = data as Record<string, unknown>
  for (const key of ['status_geral', 'kpis', 'temporal', 'clientes', 'produtos']) {
    if (!summary[key] || typeof summary[key] !== 'object' || Array.isArray(summary[key])) {
      throw new Error('A API retornou um resumo incompleto.')
    }
  }
  for (const key of ['principais_riscos', 'oportunidades', 'principais_insights']) {
    if (!Array.isArray(summary[key])) throw new Error('A API retornou um resumo incompleto.')
  }
  return data as ExecutiveSummary
}

export async function analyzeFiles(files: File[]): Promise<ExecutiveSummary> {
  const body = new FormData()
  files.forEach((file) => body.append('files', file))
  let response: Response
  try {
    // Sem timeout curto: a resposta só chega ao terminar o pipeline.
    response = await fetch(`${apiUrl}/api/analysis`, { method: 'POST', body })
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.warn('POST DataAgent: erro de rede', { url: `${apiUrl}/api/analysis`, error })
    throw new Error('A conexão com o backend foi interrompida. A análise pode ainda estar em execução; tente novamente quando a conexão estiver disponível.')
  }
  const text = await response.text()
  let result: unknown
  try { result = JSON.parse(text) } catch { result = null }
  if (!response.ok) {
    if (import.meta.env.DEV) console.warn('POST DataAgent: erro HTTP', { url: response.url, status: response.status, statusText: response.statusText, body: text })
    const detail = result && typeof result === 'object' && 'detail' in result ? result.detail : null
    throw new Error(typeof detail === 'string' ? `${detail} (HTTP ${response.status})` : `Não foi possível analisar os arquivos (HTTP ${response.status}).`)
  }
  if (!result || typeof result !== 'object' || !('summary' in result) || !('status' in result) || result.status !== 'success') {
    throw new Error('A API não retornou uma análise válida.')
  }
  return validateSummary(result.summary)
}
