import { CircleDollarSign, Lightbulb, Percent, UserRoundMinus, Users, Wallet } from 'lucide-react'
import { KpiCard } from '../components/cards/KpiCard'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { EmptyState } from '../components/common/EmptyState'
import { formatCurrency, formatInteger, formatPercentage } from '../utils/formatters'

type DisplayRanking = {
  conceito: string
  label: string
  items: { posicao: number; cliente: string; cliente_id?: string | number | null; valor: number | null }[]
}

export default function Customers() {
  return (
    <ExecutiveSummaryPage title="Clientes" description="Destaques e concentração da carteira pelas métricas disponíveis.">
      {({ clientes }) => {
        const primaryLabel = clientes.metrica_principal?.label
        const hasSemanticRankings = Object.keys(clientes.rankings ?? {}).length > 0
        const legacy = !hasSemanticRankings
        const legacyLeaders: Record<string, { cliente: string; valor: number | null } | undefined> = {
          faturamento: clientes.cliente_maior_faturamento ? { cliente: clientes.cliente_maior_faturamento.cliente, valor: clientes.cliente_maior_faturamento.faturamento } : undefined,
          valor_total: clientes.cliente_maior_valor_total ? { cliente: clientes.cliente_maior_valor_total.cliente, valor: clientes.cliente_maior_valor_total.valor_total } : undefined,
          valor_com_desconto: clientes.cliente_maior_valor_com_desconto ? { cliente: clientes.cliente_maior_valor_com_desconto.cliente, valor: clientes.cliente_maior_valor_com_desconto.valor_com_desconto } : undefined,
          lucro: clientes.cliente_maior_lucro ? { cliente: clientes.cliente_maior_lucro.cliente, valor: clientes.cliente_maior_lucro.lucro } : undefined,
          margem_bruta: clientes.cliente_maior_margem_bruta ? { cliente: clientes.cliente_maior_margem_bruta.cliente, valor: clientes.cliente_maior_margem_bruta.margem_bruta } : undefined,
        }
        const metricLabels = [
          ['faturamento', 'Faturamento'], ['valor_total', 'Valor Total'],
          ['valor_com_desconto', 'Valor com Desconto'], ['lucro', 'Lucro'],
          ['margem_bruta', 'Margem Bruta'],
        ] as const
        const leaders = metricLabels.map(([concept, label]) => ({
          concept, label,
          leader: clientes.rankings?.[concept]?.items?.[0] ?? legacyLeaders[concept],
        })).filter(item => item.leader)
        const semanticRankings = Object.values(clientes.rankings ?? {}) as DisplayRanking[]
        const legacyRankings: DisplayRanking[] = [
          ...(clientes.ranking_faturamento?.length ? [{
            conceito: 'faturamento', label: 'Faturamento',
            items: clientes.ranking_faturamento.map(item => ({
              posicao: item.posicao, cliente: item.cliente, cliente_id: item.cliente_id,
              valor: item.faturamento ?? null,
            })),
          }] : []),
          ...(clientes.ranking_lucro?.length ? [{
            conceito: 'lucro', label: 'Lucro',
            items: clientes.ranking_lucro.map(item => ({
              posicao: item.posicao, cliente: item.cliente, cliente_id: item.cliente_id,
              valor: item.lucro ?? null,
            })),
          }] : []),
        ]
        const semanticConcepts = new Set(semanticRankings.map(ranking => ranking.conceito))
        const rankings: DisplayRanking[] = [
          ...semanticRankings,
          ...legacyRankings.filter(ranking => !semanticConcepts.has(ranking.conceito)),
        ]
        const concentrationLabel = clientes.concentracao_top_5_metrica?.label ?? (clientes.concentracao_top_5 != null && legacy ? 'Faturamento' : primaryLabel)
        const participationLabel = clientes.participacao_maior_cliente_metrica?.label ?? (clientes.participacao_maior_cliente != null && legacy ? 'Faturamento' : primaryLabel)
        const negative = clientes.clientes_metrica_negativa ?? (
          clientes.clientes_resultado_negativo == null ? null
            : { conceito: 'lucro', label: 'Lucro', quantidade: clientes.clientes_resultado_negativo }
        )
        return <>
          <AnalysisSection title="Visão da base">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <KpiCard title="Quantidade de clientes" value={formatInteger(clientes.quantidade_clientes)} icon={Users} />
              {leaders.map(({ concept, label, leader }) => <KpiCard key={concept}
                title={'Cliente com maior ' + label} value={leader!.cliente}
                detail={leader!.valor == null ? undefined : label + ': ' + formatCurrency(leader!.valor)}
                icon={concept === 'margem_bruta' || concept === 'lucro' ? CircleDollarSign : Wallet} />)}
              {clientes.participacao_maior_cliente != null && <KpiCard
                title="Participação do maior cliente"
                value={formatPercentage(clientes.participacao_maior_cliente)}
                detail={participationLabel ? 'do ' + participationLabel : undefined}
                icon={Percent}
              />}
              {negative && <KpiCard
                title={negative.conceito === 'margem_bruta' ? 'Clientes com Margem Bruta negativa' : 'Clientes com ' + negative.label + ' negativo'}
                value={formatInteger(negative.quantidade)}
                detail={'Agregado por ' + negative.label}
                icon={UserRoundMinus}
              />}
            </div>
          </AnalysisSection>

          {clientes.concentracao_top_5 != null && <AnalysisSection title="Concentração Top 5">
            <div className="rounded-xl border border-line bg-surface p-5 sm:p-6">
              <p className="text-2xl font-semibold tracking-tight tabular-nums">{formatPercentage(clientes.concentracao_top_5)}</p>
              <p className="mt-3 text-sm leading-6 text-muted">
                {'Participação dos cinco principais clientes' + (concentrationLabel ? ' em ' + concentrationLabel : '') + '.'}
              </p>
              <div role="meter" aria-label="Concentração Top 5" aria-valuemin={0} aria-valuemax={100}
                aria-valuenow={clientes.concentracao_top_5} aria-valuetext={formatPercentage(clientes.concentracao_top_5)}
                className="mt-5 h-2 overflow-hidden rounded-full bg-line">
                <div className="h-full rounded-full bg-accent" style={{ width: clientes.concentracao_top_5 + '%' }} />
              </div>
            </div>
          </AnalysisSection>}

          {rankings.length > 0 ? rankings.map(({ conceito, label, items }) => <AnalysisSection key={conceito} title={'Top 10 clientes por ' + label}>
            <div className="min-w-0 overflow-x-auto rounded-xl border border-line bg-surface" tabIndex={0} role="region" aria-label={'Ranking de clientes por ' + label}>
              <table className="w-full min-w-[420px] text-left text-sm">
                <caption className="sr-only">{'Ranking de clientes por ' + label}</caption>
                <thead className="border-b border-line text-xs text-muted"><tr>
                  <th scope="col" className="p-4 font-medium">#</th>
                  <th scope="col" className="p-4 font-medium">Cliente</th>
                  <th scope="col" className="p-4 text-right font-medium">{label}</th>
                </tr></thead>
                <tbody className="divide-y divide-line">{items.map(item => <tr key={conceito + '-' + (item.cliente_id ?? item.cliente)}>
                  <td className="p-4 text-muted">{formatInteger(item.posicao)}</td>
                  <th scope="row" className="min-w-40 break-words p-4 font-medium">{item.cliente}</th>
                  <td className="whitespace-nowrap p-4 text-right">{formatCurrency(item.valor)}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </AnalysisSection>) : legacy ? <>
            <AnalysisSection title="Top 10 clientes por faturamento"><EmptyState title="Ranking por faturamento indisponível" description="Este relatório antigo não inclui esse ranking." /></AnalysisSection>
            <AnalysisSection title="Top 10 clientes por lucro"><EmptyState title="Ranking por lucro indisponível" description="Este relatório antigo não inclui esse ranking." /></AnalysisSection>
          </> : <EmptyState title="Rankings indisponíveis" description="A análise atual não possui dimensões e métricas compatíveis." />}

          {Boolean(clientes.insights_clientes?.length) && <AnalysisSection title="Insights da carteira">
            <ul className="grid gap-4 lg:grid-cols-2">
              {clientes.insights_clientes?.map((insight, index) => <li key={index} className="flex min-w-0 items-start gap-3 rounded-xl border border-line bg-surface p-5">
                <Lightbulb aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-muted" strokeWidth={1.75} />
                <p className="break-words text-sm leading-6">{insight}</p>
              </li>)}
            </ul>
          </AnalysisSection>}
        </>
      }}
    </ExecutiveSummaryPage>
  )
}
