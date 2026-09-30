import type { AnalyticalFinding } from '../../types/findings'
import { evidenceObject, formatConfidenceReason, formatFindingValue, percentageReasons } from '../../utils/findings'

const evidenceLabels: Record<string, string> = {
  registros: 'Registros analisados', registros_validos: 'Registros válidos',
  populacao: 'População considerada', total_metrica: 'Total da métrica',
  top1_valor: 'Valor do maior cliente', top5_valor: 'Valor dos cinco maiores clientes',
  top1_percentual: 'Participação do maior cliente', top5_percentual: 'Participação dos cinco maiores clientes',
  negativos: 'Resultados negativos', soma_negativos: 'Soma dos resultados negativos',
  soma_absoluta: 'Soma das magnitudes', participacao_magnitude_negativa: 'Participação da magnitude negativa',
  participacao_populacao_negativa: 'Participação negativa na população', periodos_observados: 'Períodos observados',
}

export function FindingEvidenceDetails({ finding }: { finding: AnalyticalFinding }) {
  const rows: { label: string; value: string }[] = []
  const add = (label: string, value: unknown, unit: string | null = finding.unit) => {
    const formatted = formatFindingValue(value, unit)
    if (formatted !== null) rows.push({ label, value: formatted })
  }
  const comparison = finding.comparison
  if (comparison) {
    if (comparison.previous_period) rows.push({ label: 'Período anterior', value: comparison.previous_period })
    if (comparison.current_period) rows.push({ label: 'Período atual', value: comparison.current_period })
    add('Valor anterior', comparison.previous_value)
    add('Valor atual', comparison.current_value)
    add('Variação absoluta', comparison.absolute_change)
    if (comparison.percentage_valid) add('Variação percentual', comparison.percentage_change, '%')
    if (comparison.continuous !== null) rows.push({ label: 'Continuidade', value: comparison.continuous ? 'Períodos consecutivos' : 'Períodos não consecutivos' })
  }
  for (const evidence of finding.evidence) {
    if (evidenceLabels[evidence.name]) {
      add(evidenceLabels[evidence.name], evidence.value, evidence.unit)
      if (evidence.unit === '%') {
        add(`${evidenceLabels[evidence.name]}: numerador`, evidence.numerator)
        add(`${evidenceLabels[evidence.name]}: base`, evidence.denominator)
      }
    }
    const value = evidenceObject(evidence.value)
    if (evidence.name === 'registros_por_periodo') {
      for (const [period, count] of Object.entries(value)) add(`Registros em ${period}`, count, 'count')
    }
    if (evidence.name === 'maior_cliente' && typeof value.value === 'string') rows.push({ label: 'Maior cliente', value: value.value })
    if (evidence.name === 'cobertura') {
      add('Registros de entrada', value.registros_entrada, 'count')
      add('Registros válidos para a comparação', value.registros_validos, 'count')
    }
    if (evidence.name === 'evolucao_entidade') {
      add('Participação anterior', value.previous_share, '%')
      add('Participação atual', value.current_share, '%')
      add('Variação líquida global', value.global_change)
      add('Equivalência na variação líquida', value.contribution, '%')
      add('Base da contribuição (variação líquida)', value.contribution_denominator)
      add('Queda bruta entre entidades comparáveis', value.gross_negative_change_matched)
      add('Aumento bruto entre entidades comparáveis', value.gross_positive_change_matched)
      add('Variação não explicada pelos pares comparáveis', value.unexplained_by_matched_pairs)
      const coverage = evidenceObject(value.coverage)
      for (const [period, counts] of Object.entries(coverage)) {
        const values = evidenceObject(counts)
        add(`Registros em ${period}`, values.records, 'count')
        add(`Registros com identidade e métrica em ${period}`, values.valid_identity_metric, 'count')
      }
    }
  }
  return (
    <div className="mt-4 border-t border-line pt-4 text-sm">
      <h4 className="mb-3 font-semibold">Evidências</h4>
      <dl className="grid gap-3 sm:grid-cols-2">
        {rows.map((row, index) => <div key={`${row.label}-${index}`} className="min-w-0"><dt className="text-muted">{row.label}</dt><dd className="mt-1 break-words">{row.value}</dd></div>)}
      </dl>
      {comparison && (!comparison.percentage_valid || comparison.percentage_change === null) && <p className="mt-3 text-muted">{percentageReasons[comparison.reason ?? ''] ?? 'Percentual indisponível para esta comparação.'}</p>}
      {finding.confidence_reasons.length > 0 && <><h4 className="mt-4 font-semibold">Sobre a confiança</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-muted">{finding.confidence_reasons.map((reason, index) => <li key={index}>{formatConfidenceReason(reason)}</li>)}</ul></>}
    </div>
  )
}
