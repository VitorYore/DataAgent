import { useId, useState } from 'react'
import { ChartNoAxesCombined, ChevronDown, ChevronUp } from 'lucide-react'
import type { AnalyticalFinding } from '../../types/findings'
import { findingFamily, findingFeminineLevels, findingLevels, formatFindingValue } from '../../utils/findings'
import { Badge } from '../common/Badge'
import { FindingEvidenceDetails } from '../common/FindingEvidenceDetails'

export function AnalyticalFindingCard({ finding }: { finding: AnalyticalFinding }) {
  const [expanded, setExpanded] = useState(false)
  const detailsId = useId()
  const titleId = useId()
  const delta = formatFindingValue(finding.comparison?.absolute_change, finding.unit)
  const percentage = finding.comparison?.percentage_valid ? formatFindingValue(finding.comparison.percentage_change, '%') : null
  return (
    <article aria-labelledby={titleId} className="min-w-0 rounded-xl border border-line bg-surface p-5 [overflow-wrap:anywhere] sm:p-6">
      <div className="mb-3 flex items-start gap-3">
        <ChartNoAxesCombined aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-muted" />
        <div className="min-w-0"><p className="mb-1 text-xs text-muted">{findingFamily(finding)}</p><h3 id={titleId} className="font-semibold">{finding.title}</h3></div>
      </div>
      <p className="text-sm leading-6">{finding.summary}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Badge>Prioridade: {findingFeminineLevels[finding.priority]}</Badge>
        <Badge>Impacto: {findingLevels[finding.impact]}</Badge>
        <Badge>Confiança: {findingFeminineLevels[finding.confidence]}</Badge>
      </div>
      <p className="mt-3 text-sm text-muted">{finding.metric_label}{finding.period && ` · ${finding.period.start} a ${finding.period.end}`}</p>
      {finding.entity && <p className="mt-1 text-sm">{finding.entity.label || finding.entity.value}</p>}
      {delta !== null && <p className="mt-2 text-sm">Variação: {delta}{percentage !== null && ` (${percentage})`}</p>}
      {finding.show_recommendation !== false && finding.recommendation && <div className="mt-4 rounded-lg border border-line p-3 text-sm leading-6"><h4 className="font-semibold">O que investigar</h4><p className="text-muted">{finding.recommendation}</p></div>}
      <button type="button" aria-expanded={expanded} aria-controls={detailsId} onClick={() => setExpanded(!expanded)} className="mt-4 inline-flex items-center gap-2 rounded-lg px-1 py-2 text-sm text-accent focus-visible:outline-2 focus-visible:outline-accent">
        {expanded ? 'Ocultar evidências' : 'Ver evidências'}{expanded ? <ChevronUp aria-hidden="true" className="size-4" /> : <ChevronDown aria-hidden="true" className="size-4" />}
      </button>
      <div id={detailsId} hidden={!expanded}>
        {expanded && <><FindingEvidenceDetails finding={finding} />{finding.selection_reason && <p className="mt-3 text-xs text-muted">Selecionado com prioridade {findingFeminineLevels[finding.selection_reason.priority].toLowerCase()}, impacto {findingLevels[finding.selection_reason.impact].toLowerCase()} e confiança {findingFeminineLevels[finding.selection_reason.confidence].toLowerCase()}.</p>}</>}
      </div>
    </article>
  )
}
