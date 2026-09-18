import { useEffect, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, ExternalLink, History as HistoryIcon, Minus } from 'lucide-react'
import { useNavigate } from 'react-router'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { useAnalysis } from '../contexts/AnalysisContext'
import { compareAnalyses, getAnalysisHistory } from '../services/dataAgentService'
import type { AnalysisComparison, AnalysisHistoryItem, ComparisonMetric } from '../types/dataAgent'
import { formatCurrency, formatDateTime, formatInteger, formatPercentage, formatVariation } from '../utils/formatters'

const historyLabels: Record<string, string> = {
  saudavel: 'Saudável', atencao: 'Atenção', critico: 'Crítico',
  excelente: 'Excelente', boa: 'Boa', critica: 'Crítica',
}

function displayPeriod(item?: AnalysisHistoryItem) {
  const start = item?.period?.start
  const end = item?.period?.end
  if (!start && !end) return 'Período não disponível'
  return start === end || !end ? String(start) : !start ? String(end) : `${start} – ${end}`
}

function renderMetric(metric: ComparisonMetric) {
  if (metric.percentage_point_change != null) return formatVariation(metric.percentage_point_change, true)
  if (metric.percentage_change != null) return formatVariation(metric.percentage_change)
  return `Variação absoluta: ${formatInteger(metric.absolute_change)}`
}

export default function History() {
  const navigate = useNavigate()
  const { openHistoricalAnalysis } = useAnalysis()
  const [items, setItems] = useState<AnalysisHistoryItem[]>([])
  const [left, setLeft] = useState('')
  const [right, setRight] = useState('')
  const [comparison, setComparison] = useState<AnalysisComparison | null>(null)
  const [loading, setLoading] = useState(true)
  const [comparing, setComparing] = useState(false)
  const [error, setError] = useState('')

  async function loadHistory() {
    setLoading(true)
    setError('')
    try {
      const result = await getAnalysisHistory()
      setItems(result)
      setLeft(current => current || result[1]?.id || '')
      setRight(current => current || result[0]?.id || '')
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar o histórico.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadHistory() }, [])

  async function runComparison() {
    if (!left || !right || left === right) return
    setComparing(true)
    setError('')
    try { setComparison(await compareAnalyses(left, right)) }
    catch (reason: unknown) { setError(reason instanceof Error ? reason.message : 'Não foi possível comparar as análises.') }
    finally { setComparing(false) }
  }

  async function open(item: AnalysisHistoryItem) {
    try { await openHistoricalAnalysis(item.id); navigate('/') }
    catch { /* O erro é apresentado na página pelo contexto. */ }
  }

  const leftItem = items.find(item => item.id === left)
  const rightItem = items.find(item => item.id === right)
  const metrics = comparison?.metrics ?? {}

  return <div className="space-y-8">
    <header><h1 className="text-2xl font-semibold tracking-tight">Histórico</h1><p className="mt-2 text-sm text-muted">Consulte análises concluídas e compare métricas com o mesmo significado.</p></header>

    <AnalysisSection title="Análises concluídas">
      {loading ? <p role="status" className="text-sm text-muted">Carregando histórico...</p> : error && items.length === 0 ? <div role="alert" className="space-y-3 text-sm"><p>{error}</p><button onClick={() => void loadHistory()} className="rounded-lg border border-line px-4 py-2">Tentar novamente</button></div> : items.length === 0 ? <EmptyState title="Nenhuma análise registrada ainda." description="Análises concluídas aparecerão aqui." /> : <div className="space-y-3">
        {items.map(item => <article key={item.id} className="grid min-w-0 gap-4 rounded-xl border border-line bg-surface p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:p-5">
          <div className="min-w-0"><div className="flex items-center gap-2"><HistoryIcon className="size-4 shrink-0 text-accent" aria-hidden="true" /><h2 className="break-words font-medium">{item.arquivos?.join(' + ') || 'Arquivos não disponíveis'}</h2></div>
            <p className="mt-2 text-sm text-muted">Analisada em {formatDateTime(item.created_at ?? item.data_analise)} · Dados: {displayPeriod(item)}</p>
            <p className="mt-1 text-xs text-muted">{formatInteger(item.dataset?.rows)} linhas · {formatInteger(item.dataset?.columns)} colunas · {item.available_metrics?.map(metric => metric.replaceAll('_', ' ')).join(', ') || 'Métricas não disponíveis'}</p>
            <p className="mt-1 text-xs text-muted">Status: {historyLabels[item.status_negocio || item.status || ''] || item.status_negocio || item.status || 'Não disponível'} · Qualidade: {historyLabels[String(item.quality?.classificacao_qualidade ?? '')] || item.quality?.classificacao_qualidade || 'Não disponível'}</p>
          </div>
          <button type="button" disabled={!item.report_available} onClick={() => void open(item)} className="inline-flex items-center justify-center gap-2 rounded-lg border border-line px-4 py-2 text-sm text-accent hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40" title={!item.report_available ? 'O relatório completo não foi arquivado nesta análise antiga.' : undefined}>Abrir análise <ExternalLink className="size-4" aria-hidden="true" /></button>
        </article>)}
      </div>}
    </AnalysisSection>

    <AnalysisSection title="Comparar análises">
      {items.length < 2 ? <EmptyState title="Execute uma nova análise para comparar resultados." description="A comparação fica disponível após duas análises concluídas." /> : <>
        <div className="grid gap-4 md:grid-cols-2">
          {([{value:left,onChange:setLeft,label:'Análise A'},{value:right,onChange:setRight,label:'Análise B'}] as const).map(field => <label key={field.label} className="block text-sm text-muted">{field.label}<select value={field.value} onChange={event => { field.onChange(event.target.value); setComparison(null) }} className="mt-2 w-full rounded-lg border border-line bg-surface px-3 py-3 text-text">
            {items.map(item => <option key={item.id} value={item.id}>{item.arquivos?.join(' + ') || item.id} — {formatDateTime(item.created_at ?? item.data_analise)}</option>)}
          </select><span className="mt-2 block text-xs">Período dos dados: {displayPeriod(field.label === 'Análise A' ? leftItem : rightItem)}</span></label>)}
        </div>
        <button type="button" disabled={!left || !right || left === right || comparing} onClick={() => void runComparison()} className="mt-4 rounded-lg border border-line bg-accent/10 px-4 py-3 text-sm font-medium text-accent disabled:opacity-40">{comparing ? 'Comparando...' : 'Comparar análises'}</button>
        <div className="mt-5 grid gap-4 md:grid-cols-2">{([{label:'ANÁLISE A',item:leftItem},{label:'ANÁLISE B',item:rightItem}] as const).map(({label,item}) => <article key={label} className="rounded-xl border border-line bg-surface p-4"><p className="text-xs font-medium tracking-wide text-muted">{label}</p><p className="mt-2 break-words text-sm font-medium">{item?.arquivos?.join(' + ') || 'Arquivos não disponíveis'}</p><p className="mt-1 text-xs text-muted">Executada: {formatDateTime(item?.created_at ?? item?.data_analise)}</p><p className="mt-1 text-xs text-muted">Período dos dados: {displayPeriod(item)}</p></article>)}</div>
        {error && <p role="alert" className="mt-3 text-sm text-muted">{error}</p>}
        {comparison && <div className="mt-6 space-y-6">
          {comparison.period_comparability === 'different_duration' && <p className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-4 text-sm text-muted">Os períodos têm durações diferentes. As variações são absolutas entre os conjuntos e não normalizam pela duração.</p>}
          {Object.keys(metrics).length === 0 ? <EmptyState title="Estas análises não possuem métricas semanticamente compatíveis para comparação." description="Os metadados dos períodos e das análises continuam disponíveis acima." /> : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(metrics).map(([key, metric]) => {
            if (!metric) return null
            const margin = metric.percentage_point_change != null
            const valueFormat = /quantidade|pedidos|registros/.test(key) ? formatInteger : formatCurrency
            const Direction = metric.direction === 'increase' ? ArrowUpRight : metric.direction === 'decrease' ? ArrowDownRight : Minus
            return <article key={key} className="min-w-0 rounded-xl border border-line bg-surface p-5"><h3 className="text-sm font-medium text-muted">{metric.label}</h3><div className="mt-4 grid grid-cols-2 gap-3 text-sm"><p><span className="block text-xs text-muted">A</span>{valueFormat(metric.left)}</p><p><span className="block text-xs text-muted">B</span>{valueFormat(metric.right)}</p></div><p className="mt-4 flex items-center gap-2 text-sm"><Direction className="size-4 shrink-0" aria-hidden="true" />{renderMetric(metric)}</p>{margin && <p className="mt-1 text-xs text-muted">Diferença absoluta: {formatPercentage(metric.absolute_change)}</p>}</article>
          })}</div>}
          {comparison.insights?.length ? <div><h3 className="mb-3 font-medium">Principais mudanças</h3><ul className="space-y-2">{comparison.insights.map(item => <li key={item.category} className="rounded-lg border border-line bg-surface p-4 text-sm">{item.text}</li>)}</ul></div> : null}
          {comparison.quality && Object.keys(comparison.quality).length > 0 && <div><h3 className="mb-3 font-medium">Qualidade dos dados</h3><div className="grid gap-3 sm:grid-cols-3">{Object.entries(comparison.quality).map(([key, value]) => <article key={key} className="rounded-lg border border-line bg-surface p-4 text-sm"><p className="text-muted">{key.replaceAll('_', ' ')}</p><p className="mt-2">A: {formatInteger(value.left)} · B: {formatInteger(value.right)}</p><p className="mt-1 text-xs text-muted">Diferença: {formatInteger(value.absolute_change)}</p></article>)}</div></div>}
          {comparison.temporal && <div><h3 className="mb-2 font-medium">Série temporal · {comparison.temporal.label}</h3><p className="mb-3 text-xs text-muted">Comparação somente nos períodos coincidentes entre os dois conjuntos.</p>{comparison.temporal.shared_periods.length ? <div className="overflow-x-auto rounded-xl border border-line"><table className="w-full min-w-[480px] text-left text-sm"><thead className="text-muted"><tr><th className="p-3">Período</th><th className="p-3">A</th><th className="p-3">B</th></tr></thead><tbody>{comparison.temporal.shared_periods.map(point => <tr key={point.period} className="border-t border-line"><td className="p-3">{point.period}</td><td className="p-3">{formatCurrency(point.left)}</td><td className="p-3">{formatCurrency(point.right)}</td></tr>)}</tbody></table></div> : <p className="text-sm text-muted">Não há períodos mensais coincidentes para esta métrica.</p>}</div>}
          {Object.entries(comparison.dimensions ?? {}).map(([dimension, detail]) => <div key={dimension}><h3 className="mb-3 font-medium">{dimension === 'clients' ? 'Clientes' : 'Produtos'}</h3><p className="mb-2 text-xs text-muted">Comparação por {detail.identity_reliability === 'stable_id' ? 'identificador estável' : 'label quando não há identificador disponível'}.</p><div className="overflow-x-auto rounded-xl border border-line"><table className="w-full min-w-[560px] text-left text-sm"><thead className="text-muted"><tr><th className="p-3">Entidade</th><th className="p-3">A</th><th className="p-3">B</th><th className="p-3">Variação</th></tr></thead><tbody>{detail.common.map(row => <tr key={row.id} className="border-t border-line"><td className="p-3">{row.label}</td><td className="p-3">{formatCurrency(row.left, true)}</td><td className="p-3">{formatCurrency(row.right, true)}</td><td className="p-3">{formatVariation(row.absolute_change)}</td></tr>)}</tbody></table></div><div className="mt-2 flex flex-wrap gap-4 text-xs text-muted"><span>No ranking apenas em A: {detail.only_left.map(row => row.label).join(', ') || 'Nenhum'}</span><span>No ranking apenas em B: {detail.only_right.map(row => row.label).join(', ') || 'Nenhum'}</span></div></div>)}
        </div>}
      </>}
    </AnalysisSection>
  </div>
}
