const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const categoryLabels: Record<string, string> = {
  maior_queda: 'Maior queda',
  maior_crescimento: 'Maior crescimento',
  melhor_periodo: 'Melhor período',
  tendencia_faturamento: 'Tendência de faturamento',
  tendencia_lucro: 'Tendência de lucro',
  sequencia_quedas_faturamento: 'Sequência de quedas',
  resultado_negativo: 'Resultado negativo',
  cliente_concentracao: 'Concentração de clientes',
  cliente_destaque: 'Cliente em destaque',
  produto_volume: 'Produto por volume',
  produto_faturamento: 'Produto por faturamento',
  produto_lucro: 'Produto por lucro',
  produto_rentabilidade: 'Rentabilidade de produtos',
  produto_crescimento: 'Potencial de crescimento de produtos',
  produto_devolucao: 'Devoluções de produtos',
  produto_avaliacao_positiva: 'Avaliações positivas de produtos',
  produto_avaliacao_negativa: 'Avaliações de produtos',
  estoque_ruptura: 'Risco de ruptura',
  estoque_excessivo: 'Estoque excessivo',
  canal_desempenho: 'Desempenho de canais',
  loja_desempenho: 'Desempenho de lojas',
  colaborador_desempenho: 'Desempenho de colaboradores',
}

/** Altera somente o label; filtros continuam usando a chave recebida. */
export function formatCategory(category: string): string {
  const label = categoryLabels[category] ?? category.replaceAll('_', ' ')
  return label.charAt(0).toLocaleUpperCase('pt-BR') + label.slice(1)
}

const compactCurrencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  notation: 'compact',
  compactDisplay: 'short',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
})

// A unidade apenas adiciona o símbolo, sem multiplicar o valor por 100.
const percentageFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'unit',
  unit: 'percent',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

const compactNumberFormatter = new Intl.NumberFormat('pt-BR', {
  notation: 'compact',
  compactDisplay: 'short',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
})

const integerFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 0,
})

/** Formata BRL; o modo compacto usa no máximo uma casa decimal. */
export function formatCurrency(value: number | null | undefined, compact = false): string {
  if (value == null) return 'Não disponível'
  return (compact ? compactCurrencyFormatter : currencyFormatter).format(value)
}

/** Recebe o percentual pronto: 93.98 resulta em 93,98%. */
export function formatPercentage(value: number | null | undefined): string {
  if (value == null) return 'Não disponível'
  return percentageFormatter.format(value)
}

/** Abrevia apenas a exibição, preservando o valor original. */
export function formatCompactNumber(value: number | null | undefined): string {
  if (value == null) return 'Não disponível'
  return compactNumberFormatter.format(value)
}

/** Arredonda apenas a representação visual para zero casas decimais. */
export function formatInteger(value: number | null | undefined): string {
  if (value == null) return 'Não disponível'
  return integerFormatter.format(value)
}
