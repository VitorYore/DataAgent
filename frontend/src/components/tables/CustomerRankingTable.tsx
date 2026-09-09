import type { CustomerRankingItem } from '../../types/dataAgent'
import { formatCurrency, formatInteger } from '../../utils/formatters'

export function CustomerRankingTable({ items, metric, label }: {
  items: CustomerRankingItem[]
  metric: 'faturamento' | 'lucro'
  label: string
}) {
  const secondary = metric === 'faturamento' ? 'lucro' : 'faturamento'
  const titles = { faturamento: 'Faturamento', lucro: 'Lucro' }
  return (
    <div className="min-w-0 overflow-x-auto rounded-xl border border-line bg-surface" tabIndex={0} role="region" aria-label={label}>
      <table className="w-full min-w-[540px] text-left text-sm">
        <caption className="sr-only">{label}</caption>
        <thead className="border-b border-line text-xs text-muted">
          <tr>
            <th scope="col" className="p-4 font-medium">#</th>
            <th scope="col" className="p-4 font-medium">Cliente</th>
            <th scope="col" className="p-4 text-right font-medium">{titles[metric]}</th>
            <th scope="col" className="p-4 text-right font-medium">{titles[secondary]}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {items.map((item, index) => (
            <tr key={index} className={item.posicao === 1 ? 'bg-accent/5 tabular-nums' : 'tabular-nums'}>
              <td className={`p-4 ${item.posicao === 1 ? 'font-semibold text-accent' : 'text-muted'}`}>{formatInteger(item.posicao)}</td>
              <th scope="row" className="min-w-40 max-w-80 break-words p-4 font-medium">{item.cliente}</th>
              <td className="whitespace-nowrap p-4 text-right">{formatCurrency(item[metric])}</td>
              <td className="whitespace-nowrap p-4 text-right text-muted">{formatCurrency(item[secondary])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
