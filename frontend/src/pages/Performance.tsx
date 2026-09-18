import { Banknote, CircleDollarSign, Package, Percent, Receipt, ShoppingCart, Wallet } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { KpiCard } from '../components/cards/KpiCard'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { formatCurrency, formatInteger, formatPercentage, formatSignedCurrency } from '../utils/formatters'

const PerformanceChart = lazy(() => import('../components/charts/PerformanceChart'))

export default function Performance() {
  return (
    <ExecutiveSummaryPage title="Desempenho" description="Resultados consolidados e destaques da análise temporal.">
      {({ kpis, temporal }) => {
        const metricName = temporal.nome_metrica_principal ?? 'Faturamento'
        const trend = temporal.evolucao_motivo ? undefined : temporal.tendencia_metrica ?? (!temporal.metrica_principal || temporal.metrica_principal === 'faturamento' ? temporal.tendencia_faturamento : undefined)
        const evolution = temporal.evolucao_motivo ? undefined : temporal.evolucao_metrica ?? (!temporal.metrica_principal || temporal.metrica_principal === 'faturamento' ? temporal.evolucao_faturamento : undefined)
        const bestValue = temporal.melhor_periodo?.valor ?? temporal.melhor_periodo?.faturamento
        const worstValue = temporal.pior_periodo?.valor ?? temporal.pior_periodo?.faturamento
        const series = temporal.serie_temporal ?? []
        return <>
          <AnalysisSection title="Indicadores de desempenho">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {kpis.faturamento_total != null && <KpiCard title="Faturamento" value={formatCurrency(kpis.faturamento_total, true)} detail={formatCurrency(kpis.faturamento_total)} icon={Banknote} />}
              {kpis.valor_total != null && <KpiCard title="Valor Total" value={formatCurrency(kpis.valor_total, true)} detail={formatCurrency(kpis.valor_total)} icon={Banknote} />}
              {kpis.valor_com_desconto != null && <KpiCard title="Valor com Desconto" value={formatCurrency(kpis.valor_com_desconto, true)} detail={formatCurrency(kpis.valor_com_desconto)} icon={Banknote} />}
              {kpis.lucro_total != null && <KpiCard title="Lucro" value={formatCurrency(kpis.lucro_total, true)} detail={formatCurrency(kpis.lucro_total)} icon={CircleDollarSign} />}
              {kpis.margem_bruta != null && <KpiCard title="Margem Bruta" value={formatCurrency(kpis.margem_bruta, true)} detail={formatCurrency(kpis.margem_bruta)} icon={CircleDollarSign} />}
              {kpis.custo_total != null && <KpiCard title="Custo" value={formatCurrency(kpis.custo_total, true)} detail={formatCurrency(kpis.custo_total)} icon={Wallet} />}
              {kpis.margem_lucro != null && <KpiCard title="Margem de lucro" value={formatPercentage(kpis.margem_lucro)} icon={Percent} />}
              {kpis.margem_bruta_percentual != null && <KpiCard title="Margem Bruta %" value={formatPercentage(kpis.margem_bruta_percentual)} detail={kpis.margem_bruta_percentual_metodo ?? undefined} icon={Percent} />}
              {kpis.ticket_medio != null && <KpiCard title="Ticket médio" value={formatCurrency(kpis.ticket_medio)} icon={Receipt} />}
              {kpis.quantidade_pedidos != null && <KpiCard title="Pedidos" value={formatInteger(kpis.quantidade_pedidos)} icon={ShoppingCart} />}
              {kpis.quantidade_registros != null && kpis.quantidade_pedidos == null && <KpiCard title="Registros" value={formatInteger(kpis.quantidade_registros)} icon={Receipt} />}
              {kpis.quantidade_vendida != null && <KpiCard title="Quantidade vendida" value={formatInteger(kpis.quantidade_vendida)} icon={Package} />}
            </div>
          </AnalysisSection>
          {(trend || evolution != null || temporal.evolucao_motivo || temporal.melhor_periodo || temporal.pior_periodo || temporal.maior_crescimento || temporal.maior_queda) && <AnalysisSection title="Análise temporal">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {trend && <KpiCard title={`Tendência de ${metricName === "Faturamento" ? "faturamento" : metricName}`} value={trend} />}
              {(evolution != null || temporal.evolucao_motivo) && <KpiCard title={`Evolução do ${metricName === 'Faturamento' ? 'faturamento' : metricName}`} value={evolution != null ? formatPercentage(evolution) : temporal.evolucao_motivo === 'base_muito_baixa' ? 'Base inicial muito baixa' : 'Não comparável'} detail={evolution == null ? `Variação absoluta: ${formatSignedCurrency(temporal.evolucao_variacao_absoluta)}` : undefined} />}
              {temporal.melhor_periodo && <KpiCard title="Melhor período" value={temporal.melhor_periodo.periodo} detail={formatCurrency(bestValue)} />}
              {temporal.pior_periodo && <KpiCard title="Pior período" value={temporal.pior_periodo.periodo} detail={formatCurrency(worstValue)} />}
              {temporal.maior_crescimento && <KpiCard title="Maior crescimento" value={formatPercentage(temporal.maior_crescimento.variacao)} detail={temporal.maior_crescimento.periodo} />}
              {temporal.maior_queda && <KpiCard title="Maior queda" value={formatPercentage(temporal.maior_queda.variacao)} detail={temporal.maior_queda.periodo} />}
            </div>
          </AnalysisSection>}
          <AnalysisSection title="Histórico de desempenho">
            {series.length > 0 ? <Suspense fallback={<p role="status" className="text-sm text-muted">Carregando gráfico...</p>}><PerformanceChart data={series} metricName={metricName} metricKey={temporal.metrica_principal ?? 'faturamento'} /></Suspense> : <EmptyState title="Histórico ainda indisponível" description="Os gráficos estarão disponíveis quando a análise incluir uma série de valores por período." />}
          </AnalysisSection>
        </>
      }}
    </ExecutiveSummaryPage>
  )
}
