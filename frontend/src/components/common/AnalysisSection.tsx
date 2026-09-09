import { useId } from 'react'
import type { ReactNode } from 'react'

export function AnalysisSection({ title, description, children }: {
  title: string
  description?: string
  children: ReactNode
}) {
  const id = useId()
  return (
    <section aria-labelledby={id}>
      <h2 id={id} className="mb-4 text-base font-semibold">{title}</h2>
      {description && <p className="mb-4 text-sm leading-6 text-muted">{description}</p>}
      {children}
    </section>
  )
}
