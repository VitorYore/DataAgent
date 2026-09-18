import { useState } from 'react'
import { Outlet } from 'react-router'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { HistoricalAnalysisNotice } from '../common/HistoricalAnalysisNotice'

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="min-h-dvh md:flex">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded focus:bg-surface focus:p-3">Pular para o conteúdo</a>
      <div className="md:hidden"><Header menuOpen={menuOpen} onMenuToggle={() => setMenuOpen(!menuOpen)} /></div>
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
      <div className="min-w-0 flex-1">
        <div className="hidden md:block"><Header menuOpen={menuOpen} onMenuToggle={() => setMenuOpen(!menuOpen)} /></div>
        <main id="main-content" tabIndex={-1} className="mx-auto max-w-7xl px-5 py-8 sm:p-8 lg:p-12"><HistoricalAnalysisNotice /><Outlet /></main>
      </div>
    </div>
  )
}
