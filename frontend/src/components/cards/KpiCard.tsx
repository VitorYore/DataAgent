import type { LucideIcon } from 'lucide-react'

export function KpiCard({ title, value, detail, icon: Icon }: {
  title: string
  value: string | null | undefined
  detail?: string
  icon?: LucideIcon
}) {
  return (
    <article className="min-w-0 rounded-xl border border-line bg-surface p-5 sm:p-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <h3 className="text-sm font-medium text-muted">{title}</h3>
        {Icon && <Icon aria-hidden="true" className="size-5 shrink-0 text-muted" strokeWidth={1.75} />}
      </div>
      <p className="break-words text-2xl font-semibold tracking-tight tabular-nums">{value ?? 'Não disponível'}</p>
      {detail && <p className="mt-3 break-words text-sm leading-6 text-muted">{detail}</p>}
    </article>
  )
}
