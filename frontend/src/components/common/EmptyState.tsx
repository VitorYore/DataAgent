import { PanelTop } from 'lucide-react'

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-line bg-surface p-8 text-center">
      <PanelTop aria-hidden="true" className="mb-5 size-7 text-muted" strokeWidth={1.5} />
      <h2 className="text-base font-medium">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted">{description}</p>
    </div>
  )
}
