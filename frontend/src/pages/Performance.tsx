import { Banknote, CircleDollarSign, Package, Percent, Receipt, ShoppingCart, Wallet } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { KpiCard } from '../components/cards/KpiCard'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { formatCurrency, formatInteger, formatPercentage } from '../utils/formatters'

const PerformanceChart = lazy(() => import('../components/charts/PerformanceChart'))

export default function Performance() {
  return (
    <ExecutiveSummaryPage title="Desempenho" description="Resultados consolidados e destaques da análise temporal.">
      {({ kpis, temporal }) => (
        <>
          <AnalysisSection title="Indicadores de desempenho">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <KpiCard title="Faturamento" value={formatCurrency(kpis.faturamento_total, true)} detail={formatCurrency(kpis.faturamento_total)} icon={Banknote} />
              <KpiCard title="Lucro" value={formatCurrency(kpis.lucro_total, true)} detail={formatCurrency(kpis.lucro_total)} icon={CircleDollarSign} />
              <KpiCard title="Custo" value={formatCurrency(kpis.custo_total, true)} detail={formatCurrency(kpis.custo_total)} icon={Wallet} />
              <KpiCard title="Margem de lucro" value={formatPercentage(kpis.margem_lucro)} icon={Percent} />
              <KpiCard title="Ticket médio" value={formatCurrency(kpis.ticket_medio)} icon={Receipt} />
              <KpiCard title="Pedidos" value={formatInteger(kpis.quantidade_pedidos)} icon={ShoppingCart} />
              <KpiCard title="Quantidade vendida" value={formatInteger(kpis.quantidade_vendida)} icon={Package} />
            </div>
          </AnalysisSection>
          <AnalysisSection title="Análise temporal">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <KpiCard title="Tendência de faturamento" value={temporal.tendencia_faturamento} />
              <KpiCard title="Evolução do faturamento" value={formatPercentage(temporal.evolucao_faturamento)} />
              <KpiCard title="Melhor período" value={temporal.melhor_periodo?.periodo} detail={formatCurrency(temporal.melhor_periodo?.faturamento)} />
              <KpiCard title="Pior período" value={temporal.pior_periodo?.periodo} detail={formatCurrency(temporal.pior_periodo?.faturamento)} />
              <KpiCard title="Maior crescimento" value={formatPercentage(temporal.maior_crescimento?.variacao)} detail={temporal.maior_crescimento?.periodo} />
              <KpiCard title="Maior queda" value={formatPercentage(temporal.maior_queda?.variacao)} detail={temporal.maior_queda?.periodo} />
            </div>
          </AnalysisSection>
          <AnalysisSection title="Histórico de desempenho">
            {(temporal.serie_temporal?.length ?? 0) > 0
              ? <Suspense fallback={<p role="status" className="text-sm text-muted">Carregando gráfico...</p>}><PerformanceChart data={temporal.serie_temporal ?? []} /></Suspense>
              : <EmptyState title="Histórico ainda indisponível" description="Os gráficos estarão disponíveis quando a análise incluir uma série de valores por período." />}
          </AnalysisSection>
        </>
      )}
    </ExecutiveSummaryPage>
  )
}
