import { Banknote, CircleDollarSign, Percent, Receipt, ShoppingCart, Wallet } from 'lucide-react'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { StatusCard } from '../components/cards/StatusCard'
import { KpiCard } from '../components/cards/KpiCard'
import { RiskCard } from '../components/cards/RiskCard'
import { OpportunityCard } from '../components/cards/OpportunityCard'
import { InsightCard } from '../components/cards/InsightCard'
import { formatCurrency, formatInteger, formatPercentage } from '../utils/formatters'

export default function Overview() {
  // ExecutiveSummaryPage chama dataAgentService.getExecutiveSummary()
  // e centraliza os estados de carregamento, erro e nova tentativa.
  return (
    <ExecutiveSummaryPage title="Visão geral" description="Resumo executivo e visão consolidada do negócio.">
      {(summary) => {
        if (!summary || Object.keys(summary).length === 0) {
          return <EmptyState title="Nenhuma análise disponível" description="O resumo executivo será exibido quando houver dados de análise disponíveis." />
        }
        const { status_geral, kpis, temporal, principais_riscos, oportunidades, principais_insights } = summary
        return (
          <>
            <AnalysisSection title="Resumo executivo">
              <StatusCard status={status_geral} />
            </AnalysisSection>
            <AnalysisSection title="KPIs">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <KpiCard title="Faturamento Total" value={formatCurrency(kpis.faturamento_total, true)} detail={formatCurrency(kpis.faturamento_total)} icon={Banknote} />
                <KpiCard title="Lucro Total" value={formatCurrency(kpis.lucro_total, true)} detail={formatCurrency(kpis.lucro_total)} icon={CircleDollarSign} />
                <KpiCard title="Custo Total" value={formatCurrency(kpis.custo_total, true)} detail={formatCurrency(kpis.custo_total)} icon={Wallet} />
                <KpiCard title="Margem de Lucro" value={formatPercentage(kpis.margem_lucro)} icon={Percent} />
                <KpiCard title="Ticket Médio" value={formatCurrency(kpis.ticket_medio)} icon={Receipt} />
                <KpiCard title="Pedidos" value={formatInteger(kpis.quantidade_pedidos)} icon={ShoppingCart} />
              </div>
            </AnalysisSection>
            <AnalysisSection title="Desempenho">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <KpiCard title="Tendência do faturamento" value={temporal.tendencia_faturamento} />
                <KpiCard title="Evolução do faturamento" value={formatPercentage(temporal.evolucao_faturamento)} />
                <KpiCard title="Melhor período" value={temporal.melhor_periodo?.periodo} detail={formatCurrency(temporal.melhor_periodo?.faturamento)} />
                <KpiCard title="Pior período" value={temporal.pior_periodo?.periodo} detail={formatCurrency(temporal.pior_periodo?.faturamento)} />
                <KpiCard title="Maior crescimento" value={formatPercentage(temporal.maior_crescimento?.variacao)} detail={temporal.maior_crescimento?.periodo} />
                <KpiCard title="Maior queda" value={formatPercentage(temporal.maior_queda?.variacao)} detail={temporal.maior_queda?.periodo} />
              </div>
            </AnalysisSection>
            <AnalysisSection title="Principais riscos">
              {principais_riscos.length > 0
                ? <div className="grid gap-4 xl:grid-cols-2">{principais_riscos.map((risk, index) => (
                    <div key={index} className={risk.prioridade === 'alta' ? 'min-w-0 rounded-xl border-l-2 border-amber-300/40' : 'min-w-0'}>
                      <RiskCard risk={risk} />
                    </div>
                  ))}</div>
                : <EmptyState title="Nenhum risco informado" description="A análise atual não contém riscos para exibir." />}
            </AnalysisSection>
            <AnalysisSection title="Oportunidades">
              {oportunidades.length > 0
                ? <div className="grid gap-4 xl:grid-cols-2">{oportunidades.map((opportunity, index) => <OpportunityCard key={index} opportunity={opportunity} />)}</div>
                : <EmptyState title="Nenhuma oportunidade informada" description="A análise atual não contém oportunidades para exibir." />}
            </AnalysisSection>
            <AnalysisSection title="Principais insights">
              {principais_insights.length > 0
                ? <div className="grid gap-4 xl:grid-cols-2">{principais_insights.map((insight, index) => <InsightCard key={index} insight={insight} />)}</div>
                : <EmptyState title="Nenhum insight informado" description="A análise atual não contém insights para exibir." />}
            </AnalysisSection>
          </>
        )
      }}
    </ExecutiveSummaryPage>
  )
}
