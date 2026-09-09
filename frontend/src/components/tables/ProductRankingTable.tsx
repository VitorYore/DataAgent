import type { ProductRankingItem } from '../../types/dataAgent'
import { formatCurrency, formatPercentage } from '../../utils/formatters'

const decimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 20 })
const number = (value: number | null) => value == null ? 'Não disponível' : decimal.format(value)
const currency = (value: number | null) => value == null ? 'Não disponível' : formatCurrency(value)
const percentage = (value: number | null) => value == null ? 'Não disponível' : formatPercentage(value)

export function ProductRankingTable({ items }: { items: ProductRankingItem[] }) {
  return (
    <div className="min-w-0 overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Ranking de produtos fornecido pela análise</caption>
        <thead className="border-b border-line text-xs text-muted">
          <tr>
            <th scope="col" className="p-3 font-medium">Posição</th>
            <th scope="col" className="p-3 font-medium">Produto</th>
            <th scope="col" className="hidden p-3 text-right font-medium sm:table-cell">Quantidade</th>
            <th scope="col" className="p-3 text-right font-medium">Faturamento</th>
            <th scope="col" className="hidden p-3 text-right font-medium lg:table-cell">Lucro</th>
            <th scope="col" className="hidden p-3 text-right font-medium xl:table-cell">Avaliação média</th>
            <th scope="col" className="hidden p-3 text-right font-medium xl:table-cell">Estoque atual</th>
            <th scope="col" className="hidden p-3 text-right font-medium xl:table-cell">Taxa de devolução</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {items.map((item, index) => (
            <tr key={index} className="tabular-nums">
              <td className="p-3 text-muted">{number(item.posicao)}</td>
              <th scope="row" className="max-w-48 break-words p-3 font-medium">{item.produto ?? 'Não disponível'}</th>
              <td className="hidden p-3 text-right sm:table-cell">{number(item.quantidade)}</td>
              <td className="p-3 text-right">
                <span className="sm:hidden" title={currency(item.faturamento)}>{item.faturamento == null ? 'Não disponível' : formatCurrency(item.faturamento, true)}</span>
                <span className="hidden whitespace-nowrap sm:inline">{currency(item.faturamento)}</span>
              </td>
              <td className="hidden whitespace-nowrap p-3 text-right lg:table-cell">{currency(item.lucro)}</td>
              <td className="hidden p-3 text-right xl:table-cell">{number(item.avaliacao_media)}</td>
              <td className="hidden p-3 text-right xl:table-cell">{number(item.estoque_atual)}</td>
              <td className="hidden p-3 text-right xl:table-cell">{percentage(item.taxa_devolucao)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
