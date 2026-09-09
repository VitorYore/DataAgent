import { ShieldAlert } from 'lucide-react'
import type { GeneralStatus } from '../../types/dataAgent'
import { formatInteger } from '../../utils/formatters'

export function StatusCard({ status }: { status: GeneralStatus }) {
  // Tradução visual do rótulo recebido, sem classificar pelo score.
  const label = status.status === 'critico' ? 'Crítico' : status.status
  return (
    <article className="rounded-xl border border-line bg-surface p-5 sm:p-6">
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <div>
          <div className="flex items-center gap-3 text-sm text-muted">
            <ShieldAlert aria-hidden="true" className="size-5" strokeWidth={1.75} />
            <h3>Nível de atenção</h3>
          </div>
          <p className="mt-4 text-3xl font-semibold tabular-nums">{formatInteger(status.score)} <span className="text-lg font-normal text-muted">/ 100</span></p>
          <p className="mt-3 text-sm">Status: <span className="font-medium">{label}</span></p>
          <p className="mt-3 text-xs leading-5 text-muted">Indicador de atenção da análise, não uma nota da empresa.</p>
        </div>
        <div className="min-w-0">
          <h3 className="mb-3 text-sm font-medium">Motivos principais</h3>
          {status.motivos.length > 0
            ? <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-muted">{status.motivos.map((reason, index) => <li className="break-words" key={index}>{reason}</li>)}</ul>
            : <p className="text-sm text-muted">Nenhum motivo informado na análise.</p>}
        </div>
      </div>
    </article>
  )
}
