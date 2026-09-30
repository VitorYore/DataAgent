import { test, expect } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'
import type { AnalyticalFinding } from '../src/types/findings'
import type { ExecutiveSummary } from '../src/types/dataAgent'

function finding(index = 0, overrides: Partial<AnalyticalFinding> = {}): AnalyticalFinding {
  return {
    id: `finding-${index}`, rule: 'temporal_growth', rule_version: 1, type: 'temporal_growth',
    title: `Aumento de Valor Total ${index}`, summary: 'Valor Total aumentou entre os períodos observados.',
    metric: 'valor_total', metric_label: 'Valor Total', unit: null, scope: 'temporal', entity: null,
    impact: 'high', confidence: 'medium', priority: 'medium', confidence_reasons: ['Períodos consecutivos.'],
    period: { start: '2026-01', end: '2026-02', granularity: 'M' },
    comparison: { previous_value: 100, current_value: 120, previous_period: '2026-01', current_period: '2026-02', absolute_change: 20, percentage_change: 20, percentage_valid: true, comparable: true, continuous: true, direction: 'increase', reason: null, granularity: 'M', reference_magnitude: 110 },
    evidence: [{ name: 'cobertura', value: { registros_entrada: 20, registros_validos: 20 }, unit: null, source: 'analise_temporal', concept: 'valor_total' }],
    recommendation: 'Investigar os componentes da variação observada.',
    selection_reason: { priority: 'medium', impact: 'high', confidence: 'medium', materiality: 0.5, family: 'temporal', policy: 'diversity_within_same_rank' },
    show_recommendation: index === 0, recommendation_reference: index ? 'finding-0' : null,
    ...overrides,
  }
}

function summary(total = 116, main = 8): ExecutiveSummary {
  const findings = Array.from({ length: total }, (_, index) => finding(index))
  return { ...resumoExecutivo, analysis_id: 'findings-test', achados_analiticos: findings, achados_principais: findings.slice(0, main) }
}

for (const width of [1440, 390, 320]) {
  test(`achados executivos, evidências e exploração em ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/api/analysis/latest', route => route.fulfill({ json: summary() }))
    await page.goto('/')
    const main = page.getByRole('region', { name: 'Principais Achados', exact: true })
    await expect(main.getByRole('article')).toHaveCount(8)
    await expect(main).toContainText('8 principais de 116 achados')
    await expect(main.getByText('O que investigar', { exact: true })).toHaveCount(1)
    await expect(page.getByRole('region', { name: 'Principais riscos', exact: true })).toHaveCount(0)
    const card = main.getByRole('article').first()
    await card.getByRole('button', { name: 'Ver evidências' }).press('Enter')
    await expect(card.getByRole('button')).toHaveAttribute('aria-expanded', 'true')
    await expect(card).toContainText('Valor anterior')
    await expect(card).toContainText('Variação percentual')
    await expect(card).toContainText('Confiança: Média')
    await expect(card).toContainText('impacto alto e confiança média')
    await expect(card).not.toContainText('R$')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await main.screenshot({ path: testInfo.outputPath('achados.png') })
    await main.getByRole('link', { name: 'Ver todos os achados' }).click()
    const explorer = page.getByRole('region', { name: 'Todos os achados' })
    await expect(explorer.getByRole('article')).toHaveCount(10)
    await explorer.getByRole('button', { name: 'Próxima' }).click()
    await expect(explorer).toContainText('Página 2 de 12')
    await expect(explorer.getByRole('article').first()).toContainText('Aumento de Valor Total 10')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(explorer).not.toContainText(/undefined|NaN|\[object Object\]|&amp;|&aacute;|Ã£/)
    await explorer.screenshot({ path: testInfo.outputPath('exploracao.png') })
    expect(errors).toEqual([])
  })
}

test('lista vazia difere de snapshot antigo sem findings', async ({ page }) => {
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: summary(0, 0) }))
  await page.goto('/')
  await expect(page.getByText('Nenhum achado analítico prioritário foi identificado com as evidências disponíveis.')).toBeVisible()
  await expect(page.getByRole('region', { name: 'Principais insights' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Ver todos os achados' }).click()
  await expect(page.getByText('Nenhum achado para exibir', { exact: true })).toBeVisible()
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: resumoExecutivo }))
  await page.goto('/')
  await expect(page.getByRole('region', { name: 'Principais insights' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Principais Achados' })).toHaveCount(0)
})

for (const reason of ['low_reference_base', 'zero_reference', 'negative_reference']) {
  test(`percentual indisponível e motivo humano: ${reason}`, async ({ page }) => {
    const data = summary(1, 1)
    data.achados_principais![0].comparison = { ...finding().comparison!, percentage_change: null, percentage_valid: false, reason }
    data.achados_principais![0].confidence_reasons = [`Percentual indisponível: ${reason}; conclusão baseada no delta absoluto.`]
    await page.route('**/api/analysis/latest', route => route.fulfill({ json: data }))
    await page.goto('/')
    const card = page.getByRole('region', { name: 'Principais Achados' }).getByRole('article')
    await card.getByRole('button', { name: 'Ver evidências' }).click()
    await expect(card).toContainText('Variação absoluta')
    await expect(card).not.toContainText(/0%|NaN|undefined|low_reference_base|zero_reference|negative_reference/)
    await expect(card).toContainText(/Percentual (não utilizado|indisponível)/)
  })
}

test('filtros de família, prioridade, impacto e confiança combinados', async ({ page }) => {
  const data = summary(25, 8)
  data.achados_analiticos![24] = finding(24, { scope: 'products', rule: 'product_decline', priority: 'low', impact: 'medium', confidence: 'low', entity: { id: 'P1', value: 'P1', label: 'Produto com nome extenso', identity_source: 'stable_id' } })
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: data }))
  await page.goto('/opportunities')
  await page.getByLabel('Família', { exact: true }).selectOption('Produtos')
  await page.getByLabel('Prioridade', { exact: true }).selectOption('low')
  await page.getByLabel('Impacto', { exact: true }).selectOption('medium')
  await page.getByLabel('Confiança', { exact: true }).selectOption('low')
  await expect(page.getByRole('article')).toHaveCount(1)
  await expect(page.getByRole('article')).toContainText('Produto com nome extenso')
  await page.getByLabel('Confiança', { exact: true }).selectOption('high')
  await expect(page.getByText('Nenhum achado para exibir', { exact: true })).toBeVisible()
})

test('conceitos, contribuição, concentração e negativos preservam suas evidências', async ({ page }) => {
  const data = summary(0, 0)
  data.achados_analiticos = [
    finding(0, { rule: 'customer_contributor_decline', scope: 'customers', unit: 'BRL', entity: { id: null, value: 'Cliente A', label: 'Cliente A', identity_source: 'text' }, evidence: [{ name: 'evolucao_entidade', value: { contribution: 120, contribution_denominator: -100, global_change: -100, previous_share: 20, current_share: 10, coverage: { '2026-01': { records: 50, valid_identity_metric: 45 } } }, unit: null, source: 'entity_evolution.population', concept: 'valor_total' }] }),
    finding(1, { rule: 'customer_concentration', impact: 'low', scope: 'customers', comparison: null, evidence: [{ name: 'top5_percentual', value: 22.28, numerator: 2228, denominator: 10000, unit: '%', source: 'clientes', concept: 'valor_total' }] }),
    finding(2, { rule: 'negative_results', metric: 'margem_bruta', metric_label: 'Margem Bruta', comparison: null, impact: 'low', evidence: [{ name: 'soma_negativos', value: -40.99, unit: null, source: 'clientes', concept: 'margem_bruta' }] }),
  ]
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: data }))
  await page.goto('/opportunities')
  const cards = page.getByRole('article')
  await expect(cards).toHaveCount(3)
  for (let index = 0; index < 3; index++) await cards.nth(index).getByRole('button', { name: 'Ver evidências' }).click()
  await expect(cards.nth(0)).toContainText('120%')
  await expect(cards.nth(0)).toContainText('Base da contribuição (variação líquida)')
  await expect(cards.nth(0)).toContainText('R$')
  await expect(cards.nth(1)).toContainText('22,28%')
  await expect(cards.nth(1)).not.toContainText('Faturamento')
  await expect(cards.nth(2)).toContainText('Margem Bruta')
  await expect(cards.nth(2)).toContainText('-40,99')
  await expect(cards.nth(2)).not.toContainText('Lucro')
})

test('histórico V1.5 mantém achados armazenados sem buscar latest', async ({ page }) => {
  let latestCalls = 0
  await page.route('**/api/analysis/latest', route => { latestCalls++; return route.fulfill({ json: resumoExecutivo }) })
  await page.route('**/api/analysis/stored-v15', route => route.fulfill({ json: summary(5, 4) }))
  await page.route('**/api/analysis/history', route => route.fulfill({ json: [{ id: 'stored-v15', arquivos: ['antiga.csv'], kpis: {} }] }))
  await page.addInitScript(() => localStorage.setItem('dataagent.viewing-historical-analysis-id', 'stored-v15'))
  await page.goto('/')
  await expect(page.getByRole('region', { name: 'Principais Achados' })).toContainText('4 principais de 5 achados')
  await expect(page.getByText('Visualizando análise de', { exact: false })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('region', { name: 'Principais Achados' }).getByRole('article')).toHaveCount(4)
  expect(latestCalls).toBe(0)
})

for (const decision of ['merge', 'keep_separate'] as const) {
  test(`decisão ${decision} atualiza achados pelo POST sem latest redundante`, async ({ page }) => {
    const before = summary(1, 1)
    const candidate = {
      entity_type: 'cliente', column: 'Cliente', candidate_id: 'pair-1', status: 'pending' as const,
      recommended_value: 'Empresa ABC', left: { value: 'Empresa ABC', records: 2, orders: null, metric_value: 100 },
      right: { value: 'EMPRESA ABC', records: 1, orders: null, metric_value: 50 },
      similarity: 1, confidence: 'alta' as const, reasons: ['diferenca_caixa'], metric: null, combined_preview: null,
    }
    before.dados = { ...before.dados, entity_resolution: { candidates: [candidate], can_decide: true, decisions: [], total_candidates: 1, possible_duplicate_entities: { cliente: 1 }, truncated: false, stable_id_types: [] } }
    const after = structuredClone(before)
    after.dados!.entity_resolution!.candidates[0].status = decision === 'merge' ? 'merged' : 'kept_separate'
    if (decision === 'merge') {
      after.achados_principais![0].title = 'Concentração após união confirmada'
      after.achados_principais![0].summary = 'Evidências da identidade analítica revisada.'
    }
    let latest = 0
    let posts = 0
    await page.route('**/api/analysis/latest', route => { latest++; return route.fulfill({ json: before }) })
    await page.route('**/api/analysis/findings-test/entities', async route => {
      posts++
      expect(route.request().postDataJSON()).toEqual({ candidate_id: 'pair-1', decision })
      await route.fulfill({ json: { status: 'success', files_processed: 1, summary: after } })
    })
    await page.goto('/data')
    const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
    await panel.getByRole('button', { name: decision === 'merge' ? 'Unir entidades' : 'Manter separadas', exact: true }).click()
    await panel.getByRole('button', { name: decision === 'merge' ? 'Confirmar união' : 'Confirmar separação', exact: true }).click()
    await expect(panel.getByRole('dialog')).toHaveCount(0)
    await page.getByRole('link', { name: 'Visão geral', exact: true }).click()
    const main = page.getByRole('region', { name: 'Principais Achados' })
    await expect(main).toContainText(after.achados_principais![0].title)
    expect(latest).toBe(1)
    expect(posts).toBe(1)
  })
}
