import { CircleDollarSign, Users, Wallet, Percent, UserRoundMinus, Lightbulb } from 'lucide-react'
import { KpiCard } from '../components/cards/KpiCard'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { EmptyState } from '../components/common/EmptyState'
import { CustomerRankingTable } from '../components/tables/CustomerRankingTable'
import { formatCurrency, formatInteger, formatPercentage } from '../utils/formatters'

export default function Customers() {
  return (
    <ExecutiveSummaryPage title="Clientes" description="Destaques da base de clientes e concentração de faturamento.">
      {({ clientes }) => (
        <>
          <AnalysisSection title="Visão da base">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <KpiCard title="Quantidade de clientes" value={formatInteger(clientes.quantidade_clientes)} icon={Users} />
              <KpiCard title="Cliente com maior faturamento" value={clientes.cliente_maior_faturamento?.cliente} detail={`Faturamento: ${formatCurrency(clientes.cliente_maior_faturamento?.faturamento)}`} icon={Wallet} />
              <KpiCard title="Cliente com maior lucro" value={clientes.cliente_maior_lucro?.cliente} detail={`Lucro: ${formatCurrency(clientes.cliente_maior_lucro?.lucro)}`} icon={CircleDollarSign} />
              <KpiCard title="Participação do maior cliente" value={formatPercentage(clientes.participacao_maior_cliente)} detail="do faturamento total" icon={Percent} />
              <KpiCard title="Clientes com resultado negativo" value={formatInteger(clientes.clientes_resultado_negativo)} detail="clientes com lucro agregado negativo" icon={UserRoundMinus} />
            </div>
          </AnalysisSection>
          <AnalysisSection title="Concentração Top 5">
            <div className="rounded-xl border border-line bg-surface p-5 sm:p-6">
              <p className="text-2xl font-semibold tracking-tight tabular-nums">{formatPercentage(clientes.concentracao_top_5)}</p>
              <p className="mt-3 text-sm leading-6 text-muted">Participação dos cinco principais clientes no faturamento.</p>
              {clientes.concentracao_top_5 != null && <div role="meter" aria-label="Concentração Top 5" aria-valuemin={0} aria-valuemax={100}
                aria-valuenow={clientes.concentracao_top_5} aria-valuetext={formatPercentage(clientes.concentracao_top_5)}
                className="mt-5 h-2 overflow-hidden rounded-full bg-line">
                <div className="h-full rounded-full bg-accent" style={{ width: `${clientes.concentracao_top_5}%` }} />
              </div>}
              <div aria-hidden="true" className="mt-2 flex justify-between text-xs text-muted"><span>0%</span><span>100%</span></div>
            </div>
          </AnalysisSection>
          <AnalysisSection title="Top 10 clientes por faturamento">
            {clientes.ranking_faturamento?.length
              ? <CustomerRankingTable items={clientes.ranking_faturamento} metric="faturamento" label="Ranking de clientes por faturamento" />
              : <EmptyState title="Ranking por faturamento indisponível" description="A análise atual não contém esse ranking de clientes." />}
          </AnalysisSection>
          <AnalysisSection title="Top 10 clientes por lucro">
            {clientes.ranking_lucro?.length
              ? <CustomerRankingTable items={clientes.ranking_lucro} metric="lucro" label="Ranking de clientes por lucro" />
              : <EmptyState title="Ranking por lucro indisponível" description="A análise atual não contém esse ranking de clientes." />}
          </AnalysisSection>
          {Boolean(clientes.insights_clientes?.length) && (
            <AnalysisSection title="Insights da carteira">
              <ul className="grid gap-4 lg:grid-cols-2">
                {clientes.insights_clientes?.map((insight, index) => (
                  <li key={index} className="flex min-w-0 items-start gap-3 rounded-xl border border-line bg-surface p-5">
                    <Lightbulb aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-muted" strokeWidth={1.75} />
                    <p className="break-words text-sm leading-6">{insight}</p>
                  </li>
                ))}
              </ul>
            </AnalysisSection>
          )}
        </>
      )}
    </ExecutiveSummaryPage>
  )
}
