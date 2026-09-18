import { History, RotateCcw } from 'lucide-react'
import { useAnalysis } from '../../contexts/AnalysisContext'
import { formatDateTime } from '../../utils/formatters'

export function HistoricalAnalysisNotice() {
  const { viewingHistorical, returnToLatest, processing } = useAnalysis()
  if (!viewingHistorical) return null
  return <div className="mb-6 flex flex-col gap-3 rounded-xl border border-accent/20 bg-accent/5 p-4 sm:flex-row sm:items-center sm:justify-between">
    <p className="flex items-center gap-2 text-sm"><History aria-hidden="true" className="size-4 shrink-0 text-accent" />Visualizando análise de {formatDateTime(viewingHistorical.created_at ?? viewingHistorical.data_analise)} <span className="text-muted">({viewingHistorical.id})</span></p>
    <button type="button" disabled={processing} onClick={() => void returnToLatest()} className="inline-flex items-center justify-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-accent disabled:opacity-50"><RotateCcw aria-hidden="true" className="size-4" />Análise mais recente</button>
  </div>
}
