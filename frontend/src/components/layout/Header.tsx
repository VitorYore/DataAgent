import { Menu, X } from 'lucide-react'
import { Badge } from '../common/Badge'

export function Header({ menuOpen, onMenuToggle }: { menuOpen: boolean; onMenuToggle: () => void }) {
  const Icon = menuOpen ? X : Menu
  return (
    <header className="flex min-h-20 items-center justify-between gap-4 border-b border-line px-5 sm:px-8">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onMenuToggle} aria-expanded={menuOpen} aria-controls="primary-navigation" aria-label={menuOpen ? 'Fechar navegação' : 'Abrir navegação'} className="rounded-lg p-2 text-muted hover:bg-white/5 md:hidden"><Icon aria-hidden="true" className="size-5" /></button>
        <span className="text-sm font-medium">DataAgent<span className="hidden font-normal text-muted sm:inline"> / Workspace</span></span>
      </div>
      <Badge>Estrutura inicial</Badge>
    </header>
  )
}
