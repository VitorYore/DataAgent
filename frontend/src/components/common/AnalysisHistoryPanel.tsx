import { useCallback, useEffect, useRef, useState } from 'react'
import { History, RefreshCw } from 'lucide-react'
import { useAnalysis } from '../../contexts/AnalysisContext'
import { getAnalysisHistory, getAnalysisComparison } from '../../services/dataAgentService'
import type { AnalysisHistoryItem, AnalysisComparison, Kpis } from '../../types/dataAgent'
import { formatCurrency, formatDateTime, formatInteger, formatPercentage, formatVariation } from '../../utils/formatters'
import { AnalysisSection } from './AnalysisSection'
import { EmptyState } from './EmptyState'

const statuses: Record<string, string> = { saudavel: 'Saudável', atencao: 'Atenção', critico: 'Crítico' }
const metrics: { key: keyof Kpis; title: string; margin?: boolean }[] = [
  { key: 'faturamento_total', title: 'Faturamento' }, { key: 'lucro_total', title: 'Lucro' },
  { key: 'margem_lucro', title: 'Margem', margin: true }, { key: 'ticket_medio', title: 'Ticket médio' },
]

export function AnalysisHistoryPanel() {
  const { summary, status, processing } = useAnalysis()
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([])
  const [comparison, setComparison] = useState<AnalysisComparison | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const revision = useRef(0)
  const refresh = useCallback(async () => {
    const current = ++revision.current
    setLoading(true)
    setError('')
    try {
      const [items, diff] = await Promise.all([getAnalysisHistory(), getAnalysisComparison()])
      if (current !== revision.current) return
      setHistory(items)
      setComparison(diff)
    } catch (reason: unknown) {
      if (current === revision.current) setError(reason instanceof Error ? reason.message : 'Não foi possível carregar o histórico.')
    } finally {
      if (current === revision.current) setLoading(false)
    }
  }, [])
  useEffect(() => {
    if (!processing && status !== 'idle' && status !== 'loading') void refresh()
    return () => { ++revision.current }
  }, [summary, status, processing, refresh])

  return <>
    <AnalysisSection title="Histórico de análises">
      {loading ? <p role="status" className="text-sm text-muted">Carregando histórico...</p> : error ? <div role="alert" className="rounded-xl border border-line bg-surface p-5 text-sm">
        <p>{error}</p><button onClick={() => void refresh()} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-accent"><RefreshCw className="size-4" aria-hidden="true" />Tentar novamente</button>
      </div> : history.length === 0 ? <EmptyState title="Nenhuma análise registrada ainda." description="O histórico será preenchido pelas próximas análises concluídas." /> : <div role="region" aria-label="Tabela do histórico" tabIndex={0} className="min-w-0 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[700px] text-left text-sm"><caption className="sr-only">Análises concluídas, da mais recente para a mais antiga</caption>
          <thead className="border-b border-line text-muted"><tr>{['Data/Hora', 'Arquivos analisados', 'Faturamento', 'Lucro', 'Score/status'].map(label => <th key={label} scope="col" className="p-4 font-medium">{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-line">{history.map(item => <tr key={item.id} className="tabular-nums">
            <td className="whitespace-nowrap p-4">{formatDateTime(item.data_analise)}</td>
            <td className="min-w-40 max-w-80 break-words p-4">{item.arquivos?.length ? item.arquivos.join(' + ') : 'Não disponível'}</td>
            <td className="whitespace-nowrap p-4" title={formatCurrency(item.kpis?.faturamento_total)}>{formatCurrency(item.kpis?.faturamento_total, true)}</td>
            <td className="whitespace-nowrap p-4" title={formatCurrency(item.kpis?.lucro_total)}>{formatCurrency(item.kpis?.lucro_total, true)}</td>
            <td className="p-4"><span className="inline-flex items-center gap-2"><History aria-hidden="true" className="size-4 shrink-0 text-muted" />{item.status ? statuses[item.status] ?? item.status : 'Não disponível'}</span><p className="mt-1 text-xs text-muted">Score executivo: {formatInteger(item.score)}</p></td>
          </tr>)}</tbody>
        </table>
      </div>}
    </AnalysisSection>
    <AnalysisSection title="Comparação com análise anterior">
      {loading || error ? <p className="text-sm text-muted">{loading ? 'Carregando comparação...' : 'Comparação indisponível. Tente carregar novamente.'}</p> : comparison?.status !== 'disponivel' ? <EmptyState title="Execute uma nova análise para visualizar comparações." description="São necessárias pelo menos duas análises registradas." /> : <>
        <p className="mb-4 text-sm leading-6 text-muted">Comparação das duas execuções mais recentes. Arquivos e períodos podem ser diferentes.</p>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(({ key, title, margin }) => {
          const metric = comparison.metricas[key]
          const format = margin ? formatPercentage : formatCurrency
          return <article key={key} className="min-w-0 rounded-xl border border-line bg-surface p-5"><h3 className="text-sm font-medium text-muted">{title}</h3>
            <p className="mt-4 break-words text-xl font-semibold tabular-nums">{format(metric?.atual)}</p>
            <p className="mt-3 break-words text-sm text-muted">Anterior: {format(metric?.anterior)}</p>
            <p className="mt-3 text-sm tabular-nums">Variação: {formatVariation(margin ? metric?.variacao_pontos_percentuais : metric?.variacao_percentual, margin)}</p>
          </article>
        })}</div>
      </>}
    </AnalysisSection>
  </>
}
