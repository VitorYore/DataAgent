import { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import * as service from '../services/dataAgentService'
import type { ExecutiveSummary } from '../types/dataAgent'

interface AnalysisState {
  summary: ExecutiveSummary | null
  status: 'idle' | 'loading' | 'ready' | 'empty' | 'error'
  error: string
  processing: boolean
  refreshSummary: () => Promise<void>
  analyzeFiles: (files: File[]) => Promise<void>
}

const AnalysisContext = createContext<AnalysisState | null>(null)

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null)
  const [status, setStatus] = useState<AnalysisState['status']>('idle')
  const [error, setError] = useState('')
  const [processing, setProcessing] = useState(false)
  const fetching = useRef(false)
  const uploading = useRef(false)
  const revision = useRef(0)

  const refreshSummary = useCallback(async () => {
    if (fetching.current || uploading.current) return
    fetching.current = true
    const current = ++revision.current
    setStatus('loading')
    setError('')
    try {
      const data = await service.getExecutiveSummary()
      if (revision.current !== current) return
      setSummary(data)
      setStatus(data === null ? 'empty' : 'ready')
    } catch (reason: unknown) {
      if (revision.current !== current) return
      setStatus('error')
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar a análise.')
    } finally {
      fetching.current = false
    }
  }, [])

  const analyzeFiles = useCallback(async (files: File[]) => {
    if (uploading.current) throw new Error('Uma análise já está em andamento.')
    uploading.current = true
    setProcessing(true)
    try {
      const data = await service.analyzeFiles(files)
      // Invalida uma leitura antiga ainda pendente somente após o POST ter sucesso.
      ++revision.current
      setSummary(data)
      setStatus('ready')
      setError('')
    } finally {
      uploading.current = false
      setProcessing(false)
    }
  }, [])

  return <AnalysisContext.Provider value={{ summary, status, error, processing, refreshSummary, analyzeFiles }}>{children}</AnalysisContext.Provider>
}

export function useAnalysis() {
  const context = useContext(AnalysisContext)
  if (!context) throw new Error('AnalysisProvider não foi configurado.')
  return context
}
