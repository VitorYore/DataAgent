import { Banknote, CircleDollarSign, Percent, Receipt, ShoppingCart, Wallet } from 'lucide-react'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { StatusCard } from '../components/cards/StatusCard'
import { KpiCard } from '../components/cards/KpiCard'
import { RiskCard } from '../components/cards/RiskCard'
import { OpportunityCard } from '../components/cards/OpportunityCard'
import { InsightCard } from '../components/cards/InsightCard'
import { formatCurrency, formatInteger, formatPercentage, formatSignedCurrency } from '../utils/formatters'

export default function Overview() {
  return (
    <ExecutiveSummaryPage title="Visão geral" description="Resumo executivo e visão consolidada do negócio.">
      {(summary) => {
        if (!summary || Object.keys(summary).length === 0) {
          return <EmptyState title="Nenhuma análise disponível" description="O resumo executivo será exibido quando houver dados de análise disponíveis." />
        }
        const { status_geral, kpis, temporal, principais_riscos, oportunidades, principais_insights } = summary
        const metricName = temporal.nome_metrica_principal ?? 'Faturamento'
        const trend = temporal.evolucao_motivo ? undefined : temporal.tendencia_metrica ?? (!temporal.metrica_principal || temporal.metrica_principal === 'faturamento' ? temporal.tendencia_faturamento : undefined)
        const evolution = temporal.evolucao_motivo ? undefined : temporal.evolucao_metrica ?? (!temporal.metrica_principal || temporal.metrica_principal === 'faturamento' ? temporal.evolucao_faturamento : undefined)
        const bestValue = temporal.melhor_periodo?.valor ?? temporal.melhor_periodo?.faturamento
        const worstValue = temporal.pior_periodo?.valor ?? temporal.pior_periodo?.faturamento
        const hasTemporal = Boolean(trend || evolution != null || temporal.evolucao_motivo || temporal.melhor_periodo || temporal.pior_periodo || temporal.maior_crescimento || temporal.maior_queda)
        return (
          <>
            <AnalysisSection title="Resumo executivo"><StatusCard status={status_geral} /></AnalysisSection>
            <AnalysisSection title="KPIs">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {kpis.faturamento_total != null && <KpiCard title="Faturamento Total" value={formatCurrency(kpis.faturamento_total, true)} detail={formatCurrency(kpis.faturamento_total)} icon={Banknote} />}
                {kpis.valor_total != null && <KpiCard title="Valor Total" value={formatCurrency(kpis.valor_total, true)} detail={formatCurrency(kpis.valor_total)} icon={Banknote} />}
                {kpis.valor_com_desconto != null && <KpiCard title="Valor com Desconto" value={formatCurrency(kpis.valor_com_desconto, true)} detail={formatCurrency(kpis.valor_com_desconto)} icon={Banknote} />}
                {kpis.lucro_total != null && <KpiCard title="Lucro Total" value={formatCurrency(kpis.lucro_total, true)} detail={formatCurrency(kpis.lucro_total)} icon={CircleDollarSign} />}
                {kpis.margem_bruta != null && <KpiCard title="Margem Bruta Total" value={formatCurrency(kpis.margem_bruta, true)} detail={formatCurrency(kpis.margem_bruta)} icon={CircleDollarSign} />}
                {kpis.custo_total != null && <KpiCard title="Custo Total" value={formatCurrency(kpis.custo_total, true)} detail={formatCurrency(kpis.custo_total)} icon={Wallet} />}
                {kpis.margem_lucro != null && <KpiCard title="Margem de Lucro" value={formatPercentage(kpis.margem_lucro)} icon={Percent} />}
                {kpis.margem_bruta_percentual != null && <KpiCard title="Margem Bruta %" value={formatPercentage(kpis.margem_bruta_percentual)} detail={kpis.margem_bruta_percentual_metodo ?? undefined} icon={Percent} />}
                {kpis.ticket_medio != null && <KpiCard title="Ticket Médio" value={formatCurrency(kpis.ticket_medio)} icon={Receipt} />}
                {kpis.quantidade_pedidos != null && <KpiCard title="Pedidos" value={formatInteger(kpis.quantidade_pedidos)} icon={ShoppingCart} />}
                {kpis.quantidade_registros != null && kpis.quantidade_pedidos == null && <KpiCard title="Registros" value={formatInteger(kpis.quantidade_registros)} icon={Receipt} />}
              </div>
            </AnalysisSection>
            {hasTemporal && <AnalysisSection title="Desempenho">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {trend && <KpiCard title={`Tendência de ${metricName}`} value={trend} />}
                {(evolution != null || temporal.evolucao_motivo) && <KpiCard title={`Evolução de ${metricName}`} value={evolution != null ? formatPercentage(evolution) : temporal.evolucao_motivo === 'base_muito_baixa' ? 'Base inicial muito baixa' : 'Não comparável'} detail={evolution == null ? `Variação absoluta: ${formatSignedCurrency(temporal.evolucao_variacao_absoluta)}` : undefined} />}
                {temporal.melhor_periodo && <KpiCard title="Melhor período" value={temporal.melhor_periodo.periodo} detail={formatCurrency(bestValue)} />}
                {temporal.pior_periodo && <KpiCard title="Pior período" value={temporal.pior_periodo.periodo} detail={formatCurrency(worstValue)} />}
                {temporal.maior_crescimento && <KpiCard title="Maior crescimento" value={formatPercentage(temporal.maior_crescimento.variacao)} detail={temporal.maior_crescimento.periodo} />}
                {temporal.maior_queda && <KpiCard title="Maior queda" value={formatPercentage(temporal.maior_queda.variacao)} detail={temporal.maior_queda.periodo} />}
              </div>
            </AnalysisSection>}
            <AnalysisSection title="Principais riscos">
              {principais_riscos.length > 0 ? <div className="grid gap-4 xl:grid-cols-2">{principais_riscos.map((risk, index) => <div key={index} className={risk.prioridade === 'alta' ? 'min-w-0 rounded-xl border-l-2 border-amber-300/40' : 'min-w-0'}><RiskCard risk={risk} /></div>)}</div> : <EmptyState title="Nenhum risco informado" description="A análise atual não contém riscos para exibir." />}
            </AnalysisSection>
            <AnalysisSection title="Oportunidades">
              {oportunidades.length > 0 ? <div className="grid gap-4 xl:grid-cols-2">{oportunidades.map((opportunity, index) => <OpportunityCard key={index} opportunity={opportunity} />)}</div> : <EmptyState title="Nenhuma oportunidade informada" description="A análise atual não contém oportunidades para exibir." />}
            </AnalysisSection>
            <AnalysisSection title="Principais insights">
              {principais_insights.length > 0 ? <div className="grid gap-4 xl:grid-cols-2">{principais_insights.map((insight, index) => <InsightCard key={index} insight={insight} />)}</div> : <EmptyState title="Nenhum insight informado" description="A análise atual não contém insights para exibir." />}
            </AnalysisSection>
          </>
        )
      }}
    </ExecutiveSummaryPage>
  )
}
