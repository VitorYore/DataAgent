import { test, expect } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'
import type { EntityResolution } from '../src/types/dataAgent'

const report: EntityResolution = {
  candidates: [{
    entity_type: 'cliente', column: 'Cliente',
    left: { value: 'Empresa ABC', records: 2, orders: 2, metric_value: 100 },
    right: { value: 'EMPRESA ABC', records: 1, orders: 1, metric_value: 50 },
    metric: { concept: 'valor_total', label: 'Valor Total', column: 'Valor_Total' },
    combined_preview: 150, similarity: 1, confidence: 'alta', reasons: ['diferenca_caixa'],
  }],
  total_candidates: 1, possible_duplicate_entities: { cliente: 1 }, truncated: false, stable_id_types: [],
}

for (const width of [1440, 390, 320]) {
  test('diagnostico sem acoes ou alteracoes em ' + width, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    let posts = 0
    page.on('request', request => { if (request.method() === 'POST') posts++ })
    await page.route('**/api/analysis/latest', route => route.fulfill({ json: {
      ...resumoExecutivo, dados: { ...resumoExecutivo.dados, entity_resolution: report },
    } }))
    await page.goto('/data')
    const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
    await expect(panel).toContainText('Nenhum dado foi alterado.')
    await expect(panel.getByText('Empresa ABC', { exact: true })).toBeVisible()
    await expect(panel).toContainText('Similaridade alta')
    await expect(panel).toContainText('Diferença entre maiúsculas e minúsculas')
    await expect(panel).toContainText('Possível total combinado (Valor Total): R$ 150,00')
    await expect(panel.getByRole('button')).toHaveCount(0)
    expect(posts).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('lista limitada, labels como texto e ausencia de metrica', async ({ page }) => {
  const many: EntityResolution = { ...report, total_candidates: 20, possible_duplicate_entities: { cliente: 20 },
    candidates: Array.from({ length: 20 }, (_, i) => ({ ...report.candidates[0],
      left: { value: '<script>alert(1)</script>' + i, records: 1, orders: null, metric_value: null },
      metric: null, combined_preview: null })) }
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: {
    ...resumoExecutivo, dados: { ...resumoExecutivo.dados, entity_resolution: many },
  } }))
  await page.goto('/data')
  const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
  await expect(panel.locator('article')).toHaveCount(10)
  await expect(panel).toContainText('20 possíveis duplicidades encontradas.')
  await expect(panel).toContainText('<script>alert(1)</script>0')
  await expect(panel.locator('script')).toHaveCount(0)
  await expect(panel).not.toContainText('Possível total combinado')
})

for (const width of [1440, 390, 320]) {
  test('confirmacao explicita e estado unido em ' + width, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const pending: EntityResolution = { ...report, can_decide: true, decisions: [],
      summary: { cliente: { total: 1, pending: 1, merged: 0, kept_separate: 0 } },
      candidates: [{ ...report.candidates[0], candidate_id: 'pair-a', status: 'pending', recommended_value: 'Empresa ABC' }] }
    let current = { ...resumoExecutivo, analysis_id: 'analysis-test', dados: { ...resumoExecutivo.dados, entity_resolution: pending } }
    await page.route('**/api/analysis/latest', route => route.fulfill({ json: current }))
    let posts = 0
    let release = () => {}
    const gate = new Promise<void>(resolve => { release = resolve })
    await page.route('**/api/analysis/analysis-test/entities', async route => {
      posts++
      expect(route.request().postDataJSON()).toEqual({ candidate_id: 'pair-a', decision: 'merge' })
      await gate
      current = { ...current, dados: { ...current.dados, entity_resolution: {
        ...pending, candidates: [{ ...pending.candidates[0], status: 'merged', canonical_value: 'Empresa ABC' }],
        summary: { cliente: { total: 1, pending: 0, merged: 1, kept_separate: 0 } },
        decisions: [{ candidate_id: 'pair-a', entity_type: 'cliente', column: 'Cliente',
          left: 'Empresa ABC', right: 'EMPRESA ABC', decision: 'merge', canonical_value: 'Empresa ABC',
          created_at: '2026-01-01T00:00:00Z', origin: 'user_confirmation' }],
      } } }
      await route.fulfill({ json: { status: 'success', files_processed: 1, summary: current } })
    })
    await page.goto('/data')
    const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
    await panel.getByRole('button', { name: 'Unir entidades', exact: true }).press('Enter')
    await expect(panel.getByRole('dialog')).toContainText('Os dados originais não serão alterados.')
    expect(posts).toBe(0)
    await panel.screenshot({ path: `../reports/v13-final-confirmation-${width}.png` })
    await panel.getByRole('button', { name: 'Cancelar' }).press('Enter')
    expect(posts).toBe(0)
    await panel.getByRole('button', { name: 'Unir entidades', exact: true }).click()
    await panel.getByRole('button', { name: 'Confirmar união', exact: true }).click()
    await expect(panel.getByRole('button', { name: 'Aplicando...' })).toBeDisabled()
    await expect(panel.getByRole('button', { name: 'Unir entidades', exact: true })).toBeDisabled()
    release()
    await expect(panel).toContainText('Pendentes: 0 · Unidas: 1')
    await panel.getByLabel('Estado das sugestões').selectOption('merged')
    await expect(panel).toContainText('Unidas · Label utilizado: Empresa ABC')
    await expect(panel.getByRole('button', { name: 'Unir entidades', exact: true })).toHaveCount(0)
    expect(posts).toBe(1)
    await panel.screenshot({ path: `../reports/v13-final-merged-${width}.png` })
    await page.reload()
    await panel.getByLabel('Estado das sugestões').selectOption('merged')
    await expect(panel).toContainText('Unidas · Label utilizado: Empresa ABC')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('separacao, filtros, pagina e rejeicao preservam candidato', async ({ page }) => {
  const pending: EntityResolution = { ...report, total_candidates: 12, can_decide: true,
    possible_duplicate_entities: { cliente: 11, produto: 1 },
    candidates: Array.from({ length: 12 }, (_, i) => ({ ...report.candidates[0], candidate_id: 'pair-' + i,
      entity_type: i === 11 ? 'produto' : 'cliente', recommended_value: 'Empresa ABC', status: 'pending' })) }
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: {
    ...resumoExecutivo, analysis_id: 'analysis-test', dados: { ...resumoExecutivo.dados, entity_resolution: pending },
  } }))
  let requests = 0
  await page.route('**/api/analysis/analysis-test/entities', route => {
    requests++
    if (requests === 1) return route.fulfill({ status: 422, json: { detail: 'Uniões sobrepostas não são suportadas.' } })
    expect(route.request().postDataJSON()).toEqual({ candidate_id: 'pair-10', decision: 'keep_separate' })
    return route.fulfill({ json: { status: 'success', files_processed: 1, summary: {
      ...resumoExecutivo, analysis_id: 'analysis-test', dados: { ...resumoExecutivo.dados, entity_resolution: {
        ...pending, candidates: pending.candidates.map(c => c.candidate_id === 'pair-10' ? { ...c, status: 'kept_separate' } : c),
      } },
    } } })
  })
  await page.goto('/data')
  const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
  await expect(panel.locator('article')).toHaveCount(10)
  await panel.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(panel.locator('article')).toHaveCount(2)
  await panel.getByLabel('Tipo de entidade').selectOption('produto')
  await expect(panel.locator('article')).toHaveCount(1)
  await panel.getByLabel('Tipo de entidade').selectOption('cliente')
  await panel.getByRole('button', { name: 'Próxima', exact: true }).click()
  await panel.getByRole('button', { name: 'Unir entidades', exact: true }).click()
  await panel.getByRole('button', { name: 'Confirmar união', exact: true }).click()
  await expect(panel.getByRole('alert')).toContainText('Uniões sobrepostas não são suportadas.')
  await expect(panel.locator('article')).toHaveCount(1)
  await panel.getByRole('button', { name: 'Cancelar' }).click()
  await panel.getByRole('button', { name: 'Manter separadas', exact: true }).click()
  await panel.getByRole('button', { name: 'Confirmar separação', exact: true }).click()
  await panel.getByLabel('Estado das sugestões').selectOption('kept_separate')
  await expect(panel.locator('article')).toHaveCount(1)
  await expect(panel.locator('article')).toContainText('Mantidas separadas')
})
