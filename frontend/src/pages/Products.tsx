import { Boxes, CircleDollarSign, PackageCheck, PackageMinus, PackagePlus, Wallet } from 'lucide-react'
import { ProductRankingTable } from '../components/tables/ProductRankingTable'
import { KpiCard } from '../components/cards/KpiCard'
import { AnalysisSection } from '../components/common/AnalysisSection'
import { EmptyState } from '../components/common/EmptyState'
import { ExecutiveSummaryPage } from '../components/common/ExecutiveSummaryPage'
import { formatCurrency, formatInteger } from '../utils/formatters'

export default function Products() {
  return (
    <ExecutiveSummaryPage title="Produtos" description="Destaques do portfólio e situação do estoque.">
      {({ produtos }) => (
        <>
          <AnalysisSection title="Portfólio e estoque">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <KpiCard title="Quantidade de produtos" value={formatInteger(produtos.quantidade_produtos)} icon={Boxes} />
              <KpiCard title="Produtos em risco de ruptura" value={formatInteger(produtos.produtos_risco_ruptura)} icon={PackageMinus} />
              <KpiCard title="Produtos com estoque excessivo" value={formatInteger(produtos.produtos_estoque_excessivo)} icon={PackagePlus} />
            </div>
          </AnalysisSection>
          <AnalysisSection title="Destaques de produtos">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <KpiCard title="Produto mais vendido" value={produtos.produto_mais_vendido?.produto} detail={`Quantidade vendida: ${formatInteger(produtos.produto_mais_vendido?.quantidade)}`} icon={PackageCheck} />
              <KpiCard title="Produto com maior faturamento" value={produtos.produto_maior_faturamento?.produto} detail={`Faturamento: ${formatCurrency(produtos.produto_maior_faturamento?.faturamento)}`} icon={Wallet} />
              <KpiCard title="Produto com maior lucro" value={produtos.produto_maior_lucro?.produto} detail={`Lucro: ${formatCurrency(produtos.produto_maior_lucro?.lucro)}`} icon={CircleDollarSign} />
            </div>
          </AnalysisSection>
          <AnalysisSection title="Rankings de produtos">
            {(produtos.ranking_produtos?.length ?? 0) > 0
              ? <ProductRankingTable items={produtos.ranking_produtos ?? []} />
              : <EmptyState title="Rankings ainda indisponíveis" description="Esta área receberá os rankings quando a análise disponibilizar a lista de produtos e suas posições." />}
          </AnalysisSection>
        </>
      )}
    </ExecutiveSummaryPage>
  )
}
