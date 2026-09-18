import { useEffect, useMemo, useState } from 'react'
import { Check, CircleHelp, LoaderCircle } from 'lucide-react'
import type { SemanticMappingRequest } from '../../types/dataAgent'
import { formatPercentage } from '../../utils/formatters'

const structuralLabels: Record<string, string> = {
  data: 'Data', valor_monetario: 'Valor monetário', valor_numerico: 'Valor numérico',
  identificador_provavel: 'Identificador provável', categoria_pagamento: 'Categoria de pagamento',
  texto: 'Texto', misto: 'Conteúdo misto', vazio: 'Sem valores',
}

export function SemanticMappingPanel({ request, processing, error, onConfirm }: {
  request: SemanticMappingRequest
  processing: boolean
  error: string
  onConfirm: (mappings: Record<string, string>) => Promise<void>
}) {
  const [selections, setSelections] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState('')
  const required = useMemo(() => request.required_mappings, [request.required_mappings])
  useEffect(() => { setSelections({}); setSubmitError('') }, [request.analysis_id])

  const labels = new Map(request.concepts.map((concept) => [concept.id, concept.label]))
  const detected = new Map(request.detected_columns.map((column) => [column.nome, column]))

  async function submit() {
    setSubmitError('')
    try { await onConfirm(selections) }
    catch (reason: unknown) { setSubmitError(reason instanceof Error ? reason.message : 'Não foi possível confirmar os campos.') }
  }

  return <section aria-labelledby="mapping-title" className="space-y-6 rounded-xl border border-accent/30 bg-surface p-5 sm:p-7">
    <div className="flex items-start gap-3">
      <CircleHelp aria-hidden="true" className="mt-1 size-5 shrink-0 text-accent" />
      <div>
        <h2 id="mapping-title" className="text-lg font-semibold">Confirme alguns campos</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">O DataAgent estruturou os dados, mas precisa confirmar o significado de alguns campos antes de continuar a análise.</p>
      </div>
    </div>

    {!!Object.keys(request.automatic_mappings).length && <div>
      <h3 className="text-sm font-medium">Identificado automaticamente</h3>
      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {Object.entries(request.automatic_mappings).map(([column, concept]) => {
          const profile = detected.get(column)
          return <li key={column} className="min-w-0 rounded-lg border border-line bg-canvas/40 p-4">
            <p className="text-sm font-medium">{labels.get(concept) ?? concept}</p>
            <p className="mt-1 break-all text-xs text-muted">Coluna original: {column}</p>
            <p className="mt-2 text-xs text-muted">Confiança: {formatPercentage(profile?.confianca_semantica == null ? null : profile.confianca_semantica * 100)}</p>
          </li>
        })}
      </ul>
    </div>}

    <div>
      <h3 className="text-sm font-medium">Campos que precisam de confirmação</h3>
      <div className="mt-3 grid gap-4 xl:grid-cols-2">
        {required.map(({ coluna, conceitos_compativeis }) => {
          const profile = detected.get(coluna)
          return <div key={coluna} className="min-w-0 rounded-lg border border-line bg-canvas/40 p-4 sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h4 className="font-medium">{structuralLabels[profile?.papel_estrutural ?? ''] ?? profile?.papel_estrutural ?? 'Campo não classificado'}</h4>
                <p className="mt-1 break-all text-xs text-muted">Coluna original: {coluna}</p>
              </div>
              <span className="shrink-0 text-xs text-muted">Estrutura {formatPercentage(profile?.confianca_estrutural == null ? null : profile.confianca_estrutural * 100)}</span>{profile?.sugestao_semantica && <span className="shrink-0 text-xs text-accent">Sugestão: {labels.get(profile.sugestao_semantica) ?? profile.sugestao_semantica}</span>}
            </div>
            {profile?.origem_mapeamento && <p className="mt-2 text-xs text-muted">Origem da sugestão: {profile.origem_mapeamento === 'cabecalho_posterior' ? 'cabeçalho posterior em bloco compatível' : profile.origem_mapeamento}{profile.confianca_mapeamento != null ? ` · ${formatPercentage(profile.confianca_mapeamento * 100)}` : ''}</p>}{!!profile?.exemplos.length && <div className="mt-3 flex flex-wrap gap-2">{profile.exemplos.map((example, index) => <span key={index} className="max-w-full truncate rounded-md border border-line px-2 py-1 text-xs text-muted">{example}</span>)}</div>}
            <label className="mt-4 block text-xs text-muted" htmlFor={`semantic-${request.analysis_id}-${coluna}`}>Qual significado descreve este campo?</label>
            <select id={`semantic-${request.analysis_id}-${coluna}`} value={selections[coluna] ?? ''} disabled={processing}
              onChange={(event) => setSelections((current) => ({ ...current, [coluna]: event.target.value }))}
              className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-3 text-sm text-white outline-none focus:border-accent">
              <option value="">Selecione o significado</option>
              {conceitos_compativeis.map((concept) => <option key={concept} value={concept}>{labels.get(concept) ?? concept}</option>)}
            </select>
          </div>
        })}
      </div>
    </div>
    {(error || submitError) && <p role="alert" className="text-sm leading-6 text-amber-200">{submitError || error}</p>}
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <button type="button" disabled={processing || required.some(({ coluna }) => !selections[coluna])} onClick={() => void submit()}
        className="inline-flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-5 py-3 text-sm font-medium text-accent hover:bg-accent/15 disabled:cursor-not-allowed disabled:opacity-40">
        {processing ? <><LoaderCircle aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" />Continuando análise...</> : <><Check aria-hidden="true" className="size-4" />Confirmar e analisar</>}
      </button>
      <p className="text-xs leading-5 text-muted">Os valores originais continuam preservados. Suas escolhas serão registradas no relatório da análise.</p>
    </div>
  </section>
}
