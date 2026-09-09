import type { LucideIcon } from 'lucide-react'
import { Badge } from '../common/Badge'
import { formatCategory } from '../../utils/formatters'

export function FindingCard({ title, icon: Icon, categoria, prioridade, mensagem, tipo }: {
  title: string
  icon: LucideIcon
  categoria: string
  prioridade: string
  mensagem: string
  tipo?: string
}) {
  return (
    <article className="min-w-0 rounded-xl border border-line bg-surface p-5 sm:p-6">
      <div className="mb-4 flex items-center gap-3">
        <Icon aria-hidden="true" className="size-5 shrink-0 text-muted" strokeWidth={1.75} />
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      <p className="break-words text-sm leading-6">{mensagem}</p>
      <div className="mt-4 flex flex-wrap gap-2 break-all">
        <Badge>Prioridade: {prioridade}</Badge>
        <Badge>Categoria: {formatCategory(categoria)}</Badge>
        {tipo && <Badge>Tipo: {tipo}</Badge>}
      </div>
    </article>
  )
}
