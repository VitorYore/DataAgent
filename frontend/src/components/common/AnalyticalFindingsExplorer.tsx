import { useState } from 'react'
import type { AnalyticalFinding } from '../../types/findings'
import { findingFamily, findingFeminineLevels, findingLevels } from '../../utils/findings'
import { AnalyticalFindingCard } from '../cards/AnalyticalFindingCard'
import { AnalysisSection } from './AnalysisSection'
import { EmptyState } from './EmptyState'

const PAGE_SIZE = 10

export function AnalyticalFindingsExplorer({ findings }: { findings: AnalyticalFinding[] }) {
  const [family, setFamily] = useState('')
  const [priority, setPriority] = useState('')
  const [impact, setImpact] = useState('')
  const [confidence, setConfidence] = useState('')
  const [page, setPage] = useState(0)
  const filtered = findings.filter(item => (!family || findingFamily(item) === family) && (!priority || item.priority === priority) && (!impact || item.impact === impact) && (!confidence || item.confidence === confidence))
  const families = [...new Set(findings.map(findingFamily))].sort()
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE)
  const currentPage = Math.min(page, Math.max(0, pageCount - 1))
  const filters = [
    { label: 'Família', value: family, set: setFamily, options: families.map(value => ({ value, label: value })) },
    { label: 'Prioridade', value: priority, set: setPriority, options: Object.entries(findingFeminineLevels).map(([value, label]) => ({ value, label })) },
    { label: 'Impacto', value: impact, set: setImpact, options: Object.entries(findingLevels).map(([value, label]) => ({ value, label })) },
    { label: 'Confiança', value: confidence, set: setConfidence, options: Object.entries(findingFeminineLevels).map(([value, label]) => ({ value, label })) },
  ]
  return (
    <AnalysisSection title="Todos os achados" description="Explore as evidências da análise. Os achados localizam mudanças observadas, sem afirmar suas causas.">
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {filters.map(filter => <label key={filter.label} className="min-w-0 text-sm text-muted">{filter.label}<select aria-label={filter.label} value={filter.value} onChange={event => { filter.set(event.target.value); setPage(0) }} className="mt-2 block w-full rounded-lg border border-line bg-surface p-3 text-white"><option value="">Todas as opções</option>{filter.options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>)}
      </div>
      <p role="status" className="mb-4 text-sm text-muted">{filtered.length} de {findings.length} achados{pageCount > 0 && ` · Página ${currentPage + 1} de ${pageCount}`}</p>
      {filtered.length ? <div className="grid items-start gap-4 xl:grid-cols-2">{filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE).map(finding => <AnalyticalFindingCard key={finding.id} finding={finding} />)}</div> : <EmptyState title="Nenhum achado para exibir" description="Nenhum achado corresponde às evidências disponíveis ou aos filtros selecionados." />}
      {pageCount > 1 && <nav aria-label="Paginação dos achados" className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)} className="rounded-lg border border-line px-4 py-2 text-sm disabled:opacity-40">Anterior</button><button type="button" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)} className="rounded-lg border border-line px-4 py-2 text-sm disabled:opacity-40">Próxima</button></nav>}
    </AnalysisSection>
  )
}
