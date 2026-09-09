import { BarChart3, Boxes, Database, LayoutDashboard, Lightbulb, Users } from 'lucide-react'
import { NavLink } from 'react-router'

const navigation = [
  { to: '/', label: 'Visão geral', icon: LayoutDashboard },
  { to: '/performance', label: 'Desempenho', icon: BarChart3 },
  { to: '/products', label: 'Produtos', icon: Boxes },
  { to: '/customers', label: 'Clientes', icon: Users },
  { to: '/opportunities', label: 'Oportunidades', icon: Lightbulb },
  { to: '/data', label: 'Dados', icon: Database },
]

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  return (
    <aside id="primary-navigation" className={`${open ? 'block' : 'hidden'} border-b border-line bg-surface p-5 md:sticky md:top-0 md:flex md:h-dvh md:w-60 md:shrink-0 md:flex-col md:border-r md:border-b-0`}>
      <div className="mb-10 hidden items-center gap-3 px-3 md:flex">
        <Database aria-hidden="true" className="size-6 text-accent" /><span className="text-lg font-semibold tracking-tight">DataAgent</span>
      </div>
      <p className="mb-3 px-3 text-xs font-medium uppercase tracking-widest text-muted">Workspace</p>
      <nav aria-label="Navegação principal" className="space-y-1">
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === '/'} onClick={onNavigate}
            className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-3 text-sm ${isActive ? 'bg-accent/10 font-medium text-accent' : 'text-muted hover:bg-white/5 hover:text-white'}`}>
            <Icon aria-hidden="true" className="size-5" strokeWidth={1.75} />{label}
          </NavLink>
        ))}
      </nav>
      <p className="mt-10 px-3 text-xs leading-5 text-muted md:mt-auto">Análise empresarial</p>
    </aside>
  )
}
