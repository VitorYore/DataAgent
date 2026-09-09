import { Route, Routes, Link } from 'react-router'
import { AppLayout } from './components/layout/AppLayout'
import { EmptyState } from './components/common/EmptyState'
import Overview from './pages/Overview'
import Performance from './pages/Performance'
import Products from './pages/Products'
import Customers from './pages/Customers'
import Opportunities from './pages/Opportunities'
import Data from './pages/Data'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Overview />} />
        <Route path="performance" element={<Performance />} />
        <Route path="products" element={<Products />} />
        <Route path="customers" element={<Customers />} />
        <Route path="opportunities" element={<Opportunities />} />
        <Route path="data" element={<Data />} />
        <Route path="*" element={<><EmptyState title="Página não encontrada" description="Este endereço não está disponível." /><Link to="/" className="mt-6 inline-block text-sm text-accent underline">Voltar para visão geral</Link></>} />
      </Route>
    </Routes>
  )
}
