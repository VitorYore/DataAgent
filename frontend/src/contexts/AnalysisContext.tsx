import { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import * as service from '../services/dataAgentService'
import type { AnalysisHistoryItem, ExecutiveSummary, SemanticMappingRequest } from '../types/dataAgent'

interface AnalysisState {
  summary: ExecutiveSummary | null
  status: 'idle' | 'loading' | 'ready' | 'empty' | 'error' | 'mapping_required'
  error: string
  processing: boolean
  mappingRequest: SemanticMappingRequest | null
  viewingHistorical: AnalysisHistoryItem | null
  refreshSummary: () => Promise<void>
  analyzeFiles: (files: File[]) => Promise<boolean>
  confirmMapping: (mappings: Record<string, string>) => Promise<void>
  openHistoricalAnalysis: (id: string) => Promise<void>
  returnToLatest: () => Promise<void>
}

const PENDING_ID_KEY = 'dataagent.pending-analysis-id'
const HISTORICAL_ID_KEY = 'dataagent.viewing-historical-analysis-id'
const AnalysisContext = createContext<AnalysisState | null>(null)

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null)
  const [status, setStatus] = useState<AnalysisState['status']>('idle')
  const [error, setError] = useState('')
  const [processing, setProcessing] = useState(false)
  const [mappingRequest, setMappingRequest] = useState<SemanticMappingRequest | null>(null)
  const [viewingHistorical, setViewingHistorical] = useState<AnalysisHistoryItem | null>(null)
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
      const pendingId = window.localStorage.getItem(PENDING_ID_KEY)
      if (pendingId) {
        try {
          const pending = await service.getPendingMapping(pendingId)
          if (revision.current !== current) return
          setMappingRequest(pending)
          setSummary(null)
          setStatus('mapping_required')
          return
        } catch (reason: unknown) {
          if (!(reason instanceof Error) || !reason.message.includes('HTTP 404')) throw reason
          window.localStorage.removeItem(PENDING_ID_KEY)
        }
      }
      const historicalId = window.localStorage.getItem(HISTORICAL_ID_KEY)
      if (historicalId) {
        try {
          const [historicalSummary, history] = await Promise.all([service.getAnalysis(historicalId), service.getAnalysisHistory()])
          if (revision.current !== current) return
          setSummary(historicalSummary)
          setViewingHistorical(history.find(item => item.id === historicalId) ?? { id: historicalId })
          setMappingRequest(null)
          setStatus('ready')
          return
        } catch (reason: unknown) {
          if (!(reason instanceof Error) || !reason.message.includes('404')) throw reason
          window.localStorage.removeItem(HISTORICAL_ID_KEY)
          setViewingHistorical(null)
        }
      }
      setMappingRequest(null)
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
      ++revision.current
      window.localStorage.removeItem(HISTORICAL_ID_KEY)
      setViewingHistorical(null)
      if (data.status === 'mapping_required') {
        window.localStorage.setItem(PENDING_ID_KEY, data.analysis_id)
        setMappingRequest(data)
        setSummary(null)
        setStatus('mapping_required')
        return false
      } else {
        window.localStorage.removeItem(PENDING_ID_KEY)
        setMappingRequest(null)
        setSummary(data.summary)
        setStatus('ready')
        setError('')
        return true
      }
    } finally {
      uploading.current = false
      setProcessing(false)
    }
  }, [])

  const confirmMapping = useCallback(async (mappings: Record<string, string>) => {
    if (uploading.current || !mappingRequest) return
    uploading.current = true
    setProcessing(true)
    setError('')
    try {
      const response = await service.confirmAnalysisMapping(mappingRequest.analysis_id, mappings)
      window.localStorage.removeItem(HISTORICAL_ID_KEY)
      setViewingHistorical(null)
      if (response.status !== 'success') throw new Error('A confirmação ainda requer mapeamento adicional.')
      ++revision.current
      setSummary(response.summary)
      setMappingRequest(null)
      setStatus('ready')
      window.localStorage.removeItem(PENDING_ID_KEY)
    } catch (reason: unknown) {
      const message = reason instanceof Error ? reason.message : 'Não foi possível continuar a análise.'
      setError(message)
      throw reason
    } finally {
      uploading.current = false
      setProcessing(false)
    }
  }, [mappingRequest])

  const openHistoricalAnalysis = useCallback(async (id: string) => {
    setStatus('loading')
    setError('')
    try {
      const [historicalSummary, history] = await Promise.all([service.getAnalysis(id), service.getAnalysisHistory()])
      ++revision.current
      window.localStorage.setItem(HISTORICAL_ID_KEY, id)
      setSummary(historicalSummary)
      setViewingHistorical(history.find(item => item.id === id) ?? { id })
      setMappingRequest(null)
      setStatus('ready')
    } catch (reason: unknown) {
      setStatus('error')
      setError(reason instanceof Error ? reason.message : 'Unable to open historical analysis.')
      throw reason
    }
  }, [])

  const returnToLatest = useCallback(async () => {
    window.localStorage.removeItem(HISTORICAL_ID_KEY)
    setViewingHistorical(null)
    await refreshSummary()
  }, [refreshSummary])

  return <AnalysisContext.Provider value={{ summary, status, error, processing, mappingRequest, viewingHistorical, refreshSummary, analyzeFiles, confirmMapping, openHistoricalAnalysis, returnToLatest }}>{children}</AnalysisContext.Provider>
}

export function useAnalysis() {
  const context = useContext(AnalysisContext)
  if (!context) throw new Error('AnalysisProvider não foi configurado.')
  return context
}
