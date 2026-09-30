import type { AnalyticalFinding, EvidenceValue } from '../types/findings'
import { formatCurrency, formatInteger, formatPercentage } from './formatters'

export const findingLevels = { high: 'Alto', medium: 'Médio', low: 'Baixo' }
export const findingFeminineLevels = { high: 'Alta', medium: 'Média', low: 'Baixa' }

export function formatConfidenceReason(reason: string): string {
  const readable = reason.replace('Identidade: text;', 'Identidade baseada no nome;')
    .replace('Identidade: stable_id;', 'Identidade baseada em identificador estável;')
    .replace('Identidade: confirmed_alias;', 'Identidade confirmada na revisão;')
  for (const [code, explanation] of Object.entries(percentageReasons)) {
    if (readable.includes(code)) return `${explanation} A conclusão utiliza a variação absoluta.`
  }
  return readable
}

export function findingFamily(finding: AnalyticalFinding): string {
  if (finding.rule === 'customer_concentration') return 'Concentração'
  if (finding.rule === 'negative_results') return 'Resultados negativos'
  if (finding.rule.startsWith('temporal_')) return 'Temporal'
  if (finding.scope === 'customers') return 'Clientes'
  if (finding.scope === 'products') return 'Produtos'
  return 'Outros'
}

export function evidenceObject(value: EvidenceValue | undefined): { [key: string]: EvidenceValue } {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

export function formatFindingValue(value: unknown, unit?: string | null): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  if (unit === '%') return formatPercentage(value)
  if (unit === 'count') return formatInteger(value)
  if (unit === 'BRL') return formatCurrency(value)
  // Só apresentar moeda quando a unidade foi explicitamente informada.
  if (unit && /^[A-Z]{3}$/.test(unit)) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: unit }).format(value)
  }
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value)
}

export const percentageReasons: Record<string, string> = {
  zero_reference: 'Percentual indisponível: o valor anterior é zero.',
  negative_reference: 'Percentual não utilizado: a base de comparação é negativa.',
  low_reference_base: 'Percentual não utilizado: a base de comparação é muito pequena.',
  sign_change: 'Percentual não utilizado: houve mudança de sinal entre os valores.',
  non_consecutive_periods: 'Comparação entre períodos não consecutivos.',
  invalid_period: 'Os períodos disponíveis não permitem uma comparação válida.',
  invalid_value: 'Valores insuficientes para a comparação.',
  invalid_percentage: 'Percentual indisponível para esta comparação.',
}
