import { useRef, useState } from 'react'
import { Users, LoaderCircle } from 'lucide-react'
import type { EntityCandidate, EntityResolution } from '../../types/dataAgent'
import { formatCurrency, formatInteger } from '../../utils/formatters'
import { AnalysisSection } from './AnalysisSection'

const reasons: Record<string, string> = {
  diferenca_acentuacao: 'Diferença de acentuação',
  diferenca_espacamento: 'Diferença de espaços',
  diferenca_caixa: 'Diferença entre maiúsculas e minúsculas',
  grafia_muito_semelhante: 'Grafia muito semelhante',
}
const kinds: Record<string, string> = {
  cliente: 'Clientes', produto: 'Produtos', categoria: 'Categorias', loja: 'Lojas', colaborador: 'Colaboradores',
}
const statuses = { pending: 'Pendentes', merged: 'Unidas', kept_separate: 'Mantidas separadas' }
type Status = keyof typeof statuses
type Decision = 'merge' | 'keep_separate'

export function EntityResolutionPanel({ report, processing = false, onDecide }: {
  report: EntityResolution
  processing?: boolean
  onDecide?: (id: string, decision: Decision) => Promise<void>
}) {
  const [status, setStatus] = useState<Status>('pending')
  const [kind, setKind] = useState('')
  const [page, setPage] = useState(0)
  const [confirmation, setConfirmation] = useState<{ candidate: EntityCandidate; decision: Decision } | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const sending = useRef(false)
  const candidates = report.candidates.filter(c => (c.status ?? 'pending') === status && (!kind || c.entity_type === kind))
  const lastPage = Math.max(0, Math.ceil(candidates.length / 10) - 1)
  const currentPage = Math.min(page, lastPage)
  const editable = report.can_decide && onDecide
  const disabled = processing || busy

  async function confirm() {
    if (!confirmation?.candidate.candidate_id || !onDecide || sending.current || disabled) return
    sending.current = true
    setBusy(true)
    setError('')
    try {
      await onDecide(confirmation.candidate.candidate_id, confirmation.decision)
      setConfirmation(null)
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível aplicar a decisão.')
    } finally {
      sending.current = false
      setBusy(false)
    }
  }

  return <AnalysisSection title="Possíveis duplicidades">
    <div className="rounded-xl border border-line bg-surface p-5">
      <p className="flex items-center gap-2 text-sm"><Users className="size-5 shrink-0" aria-hidden="true" />
        O DataAgent encontrou nomes muito parecidos que podem representar a mesma entidade. Nenhuma união é feita sem sua confirmação.
      </p>
      {!report.decisions?.some(d => d.decision === 'merge') && <p className="mt-2 text-xs text-muted">Nenhum dado foi alterado.</p>}
      <ul className="mt-3 space-y-2 text-sm">
        {Object.entries(report.possible_duplicate_entities).map(([type, total]) => {
          const count = report.summary?.[type]
          return <li key={type}>{kinds[type] ?? type}: {total}
            {count && <span className="text-muted"> · Pendentes: {count.pending} · Unidas: {count.merged} · Mantidas separadas: {count.kept_separate}</span>}
          </li>
        })}
      </ul>
      <p className="mt-3 text-xs text-muted">{formatInteger(report.total_candidates)} possíveis duplicidades encontradas. Exibindo até 10 sugestões por página.</p>
      {!editable && <p className="mt-2 text-xs text-muted">Diagnóstico somente para consulta. Execute uma nova análise para habilitar decisões.</p>}
      {report.truncated && <p className="mt-2 text-xs text-muted">O relatório contém somente os primeiros 500 candidatos. A contagem inclui sugestões não listadas.</p>}
    </div>
    <div className="mt-4 flex flex-wrap gap-3 text-sm">
      <label>Estado <select aria-label="Estado das sugestões" value={status} disabled={disabled} onChange={e => { setStatus(e.target.value as Status); setPage(0); setConfirmation(null) }} className="rounded border border-line bg-surface p-2">
        {Object.entries(statuses).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>Entidade <select aria-label="Tipo de entidade" value={kind} disabled={disabled} onChange={e => { setKind(e.target.value); setPage(0); setConfirmation(null) }} className="rounded border border-line bg-surface p-2">
        <option value="">Todas</option>
        {Object.keys(report.possible_duplicate_entities).map(type => <option key={type} value={type}>{kinds[type] ?? type}</option>)}
      </select></label>
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-amber-300">{error}</p>}
    <div className="mt-4 space-y-4">
      {candidates.slice(currentPage * 10, currentPage * 10 + 10).map((candidate, index) =>
        <article key={candidate.candidate_id ?? index} className="rounded-xl border border-line bg-surface p-5">
          <h3 className="text-sm font-medium">{kinds[candidate.entity_type] ?? candidate.entity_type}</h3>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {[candidate.left, candidate.right].map(side => <div key={side.value} className="min-w-0">
              <p className="break-words font-medium">{side.value}</p>
              <p className="mt-1 text-xs text-muted">{formatInteger(side.records)} registros{side.orders != null ? ' · ' + formatInteger(side.orders) + ' pedidos' : ''}</p>
              {side.metric_value != null && <p className="mt-1 text-sm">{candidate.metric?.label}: {formatCurrency(side.metric_value)}</p>}
            </div>)}
          </div>
          <p className="mt-3 text-xs text-muted">Similaridade {candidate.confidence === 'alta' ? 'alta' : 'média'} · {candidate.reasons.map(reason => reasons[reason] ?? reason).join('; ')}</p>
          {candidate.combined_preview != null && <p className="mt-3 text-sm">Possível total combinado ({candidate.metric?.label}): {formatCurrency(candidate.combined_preview)}</p>}
          {candidate.status === 'merged' && <p className="mt-3 text-sm">Unidas · Label utilizado: {candidate.canonical_value}</p>}
          {candidate.status === 'kept_separate' && <p className="mt-3 text-sm">Mantidas separadas</p>}
          {editable && candidate.candidate_id && (candidate.status ?? 'pending') === 'pending' && <div className="mt-4 flex flex-wrap gap-3">
            <button disabled={disabled} onClick={() => { setConfirmation({ candidate, decision: 'merge' }); setError('') }} className="rounded-lg border border-line px-4 py-2 text-sm text-accent disabled:opacity-40">Unir entidades</button>
            <button disabled={disabled} onClick={() => { setConfirmation({ candidate, decision: 'keep_separate' }); setError('') }} className="rounded-lg border border-line px-4 py-2 text-sm disabled:opacity-40">Manter separadas</button>
          </div>}
          {confirmation && confirmation.candidate.candidate_id === candidate.candidate_id && candidate.candidate_id && <div role="dialog" aria-label="Confirmar decisão" className="mt-4 rounded-xl border border-accent/40 p-4 text-sm">
            <p className="font-medium">{confirmation.decision === 'merge' ? 'Confirmar união?' : 'Manter essas entidades separadas?'}</p>
            <p className="mt-2 text-muted">{confirmation.decision === 'merge'
              ? 'Os dados originais não serão alterados. As análises passarão a tratar esses nomes como a mesma entidade.'
              : 'A sugestão deixará de ser pendente. Os agrupamentos continuarão separados.'}</p>
            {confirmation.decision === 'merge' && <p className="mt-2 break-words">Label recomendado: {candidate.recommended_value}</p>}
            <div className="mt-3 flex flex-wrap gap-3">
              <button disabled={disabled} onClick={() => setConfirmation(null)} className="rounded border border-line px-3 py-2">Cancelar</button>
              <button disabled={disabled} onClick={() => void confirm()} className="inline-flex items-center gap-2 rounded border border-accent/40 px-3 py-2 text-accent disabled:opacity-40">
                {disabled && <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />}
                {disabled ? 'Aplicando...' : confirmation.decision === 'merge' ? 'Confirmar união' : 'Confirmar separação'}
              </button>
            </div>
          </div>}
        </article>)}
    </div>
    {!candidates.length && <p className="mt-4 text-sm text-muted">Nenhuma sugestão neste filtro.</p>}
    {candidates.length > 10 && <div className="mt-4 flex items-center gap-4 text-sm">
      <button disabled={disabled || currentPage === 0} onClick={() => setPage(currentPage - 1)}>Anterior</button>
      <span>Página {currentPage + 1} de {lastPage + 1}</span>
      <button disabled={disabled || currentPage === lastPage} onClick={() => setPage(currentPage + 1)}>Próxima</button>
    </div>}
  </AnalysisSection>
}
