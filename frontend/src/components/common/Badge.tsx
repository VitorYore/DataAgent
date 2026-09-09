import type { ReactNode } from 'react'

export function Badge({ children }: { children: ReactNode }) {
  return <span className="inline-flex rounded-md border border-line px-2 py-1 text-xs font-medium text-muted">{children}</span>
}
