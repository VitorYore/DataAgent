import { useState } from 'react'
import { OpportunityCard } from '../components/cards/OpportunityCard'
import { RiskCard } from '../components/cards/RiskCard'
import { InsightCard } from '../components/cards/InsightCard'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import type { ExecutiveSummary } from '../types/dataAgent'
import { formatCategory } from '../utils/formatters'

function Findings({ summary }: { summary: ExecutiveSummary }) {
  const [priority, setPriority] = useState('')
  const [category, setCategory] = useState('')
  const all = [...summary.oportunidades, ...summary.principais_riscos, ...summary.principais_insights]
  const priorities = [...new Set(all.map((item) => item.prioridade))]
  const categories = [...new Set(all.map((item) => item.categoria))]
  const matches = (item: { prioridade: string; categoria: string }) =>
    (!priority || item.prioridade === priority) && (!category || item.categoria === category)
  const opportunities = summary.oportunidades.filter(matches)
  const risks = summary.principais_riscos.filter(matches)
  const insights = summary.principais_insights.filter(matches)
  const emptyDescription = priority || category
    ? 'Nenhum resultado corresponde aos filtros selecionados.'
    : 'A análise atual não contém resultados nesta seção.'

  return (
    <>
      <div className="grid gap-4 rounded-xl border border-line bg-surface p-5 sm:grid-cols-2 sm:p-6">
        <label className="min-w-0 text-sm text-muted">
          Prioridade
          <select aria-label="Prioridade" value={priority} onChange={(event) => setPriority(event.target.value)} className="mt-2 block w-full rounded-lg border border-line bg-canvas p-3 text-sm text-white">
            <option value="">Todas as prioridades</option>
            {priorities.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        <label className="min-w-0 text-sm text-muted">
          Categoria
          <select aria-label="Categoria" value={category} onChange={(event) => setCategory(event.target.value)} className="mt-2 block w-full rounded-lg border border-line bg-canvas p-3 text-sm text-white">
            <option value="">Todas as categorias</option>
            {categories.map((value) => <option key={value} value={value}>{formatCategory(value)}</option>)}
          </select>
        </label>
      </div>
      <AnalysisSection title="Oportunidades">
        {opportunities.length > 0
          ? <div className="grid gap-4 xl:grid-cols-2">{opportunities.map((item, index) => <OpportunityCard key={index} opportunity={item} />)}</div>
          : <EmptyState title="Nenhuma oportunidade para exibir" description={emptyDescription} />}
      </AnalysisSection>
      <AnalysisSection title="Pontos de Atenção">
        {risks.length > 0
          ? <div className="grid gap-4 xl:grid-cols-2">
              {risks.map((item, index) => <RiskCard key={`risk-${index}`} risk={item} />)}
            </div>
          : <EmptyState title="Nenhum ponto de atenção para exibir" description={emptyDescription} />}
      </AnalysisSection>
      <AnalysisSection title="Insights">
        {insights.length > 0
          ? <div className="grid gap-4 xl:grid-cols-2">{insights.map((item, index) => <InsightCard key={index} insight={item} />)}</div>
          : <EmptyState title="Nenhum insight para exibir" description={emptyDescription} />}
      </AnalysisSection>
    </>
  )
}

export default function Opportunities() {
  return (
    <ExecutiveSummaryPage title="Oportunidades" description="Oportunidades, riscos e insights identificados pela análise.">
      {(summary) => <Findings summary={summary} />}
    </ExecutiveSummaryPage>
  )
}
