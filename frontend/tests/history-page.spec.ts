import { expect, test } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

const entries = [
  { id: 'analysis-new', report_available: true, created_at: '2026-09-10T10:00:00Z', arquivos: ['b.csv'], dataset: { rows: 20, columns: 4 }, period: { start: '2026-09', end: '2026-09' }, available_metrics: ['valor_total', 'quantidade_pedidos'] },
  { id: 'analysis-old', report_available: true, created_at: '2026-09-09T10:00:00Z', arquivos: ['a.csv'], dataset: { rows: 10, columns: 4 }, period: { start: '2026-08', end: '2026-08' }, available_metrics: ['valor_total', 'quantidade_pedidos'] },
]

test('seleciona duas análises, compara conceitos comuns e abre histórico', async ({ page }) => {
  let comparedUrl = ''
  await page.route('**/api/analysis/history', route => route.fulfill({ json: entries }))
  await page.route('**/api/analysis/compare?*', route => {
    comparedUrl = route.request().url()
    return route.fulfill({ json: {
      status: 'disponivel', left_analysis: 'analysis-old', right_analysis: 'analysis-new',
      periods: { left: entries[1].period, right: entries[0].period }, period_comparability: 'same_duration',
      metrics: { valor_total: { concept: 'valor_total', label: 'Valor Total', left: 100, right: 120, absolute_change: 20, percentage_change: 20, direction: 'increase' } },
      metricas: {}, dimensions: {}, insights: [{ category: 'comparison_valor_total', type: 'informativo', priority: 'media', text: 'Valor Total aumentou 20% entre as análises.' }],
    } })
  })
  await page.route('**/api/analysis/analysis-old', route => route.fulfill({ json: { ...resumoExecutivo, analysis_id: 'analysis-old' } }))
  await page.goto('/history')
  await expect(page.getByRole('heading', { name: 'a.csv', exact: true })).toBeVisible()
  await page.getByRole('combobox').nth(0).selectOption('analysis-old')
  await page.getByRole('combobox').nth(1).selectOption('analysis-new')
  await page.getByRole('button', { name: 'Comparar análises' }).click()
  await expect(page.getByRole('heading', { name: 'Valor Total' })).toBeVisible()
  await expect(page.getByText('Valor Total aumentou 20% entre as análises.')).toBeVisible()
  expect(comparedUrl).toContain('left=analysis-old')
  expect(comparedUrl).toContain('right=analysis-new')
  await page.getByRole('button', { name: 'Abrir análise' }).nth(1).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByText(/Visualizando análise de/)).toBeVisible()
  await page.getByRole('button', { name: 'Análise mais recente' }).click()
  await expect(page.getByText(/Visualizando análise de/)).toHaveCount(0)
})

test('não envia comparação quando a mesma análise está selecionada', async ({ page }) => {
  await page.route('**/api/analysis/history', route => route.fulfill({ json: entries }))
  let compareCalls = 0
  await page.route('**/api/analysis/compare?*', route => { compareCalls++; return route.fulfill({ json: { status: 'insuficiente', metricas: {} } }) })
  await page.goto('/history')
  await page.getByRole('combobox').nth(0).selectOption('analysis-new')
  await page.getByRole('combobox').nth(1).selectOption('analysis-new')
  await expect(page.getByRole('button', { name: 'Comparar análises' })).toBeDisabled()
  expect(compareCalls).toBe(0)
})


test('normalizes legacy HTML entities without modifying already-lost text', async ({ page }) => {
  const legacy = [{
    ...entries[0],
    arquivos: ['per?odo.csv'],
    status: 'N&atilde;o dispon&iacute;vel',
    quality: { classificacao_qualidade: 'Aten&ccedil;&atilde;o' },
  }]
  await page.route('**/api/analysis/history', route => route.fulfill({ json: legacy }))
  await page.goto('/history')
  await expect(page.getByText('Status: N\u00e3o dispon\u00edvel \u00b7 Qualidade: Aten\u00e7\u00e3o')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'per?odo.csv' })).toBeVisible()
  await expect(page.getByText(/&atilde;|&iacute;|&ccedil;/)).toHaveCount(0)
  const mojibake = new RegExp(String.fromCharCode(0xc3) + '|' + String.fromCharCode(0xc2))
  await expect(page.getByText(mojibake)).toHaveCount(0)
})

const historicalTexts = [
  ['An&aacute;lise Per&iacute;odo M&eacute;tricas Hist&oacute;rico Compara&ccedil;&atilde;o Qualidade Cr&iacute;tica Aten&ccedil;&atilde;o Evolu&ccedil;&atilde;o Participa&ccedil;&atilde;o Concentra&ccedil;&atilde;o', 'Análise Período Métricas Histórico Comparação Qualidade Crítica Atenção Evolução Participação Concentração'],
  ['N&atilde;o dispon&iacute;vel', 'N\u00e3o dispon\u00edvel'],
  ['Qualidade cr&iacute;tica', 'Qualidade cr\u00edtica'],
  ['Qualidade cr\u00edtica', 'Qualidade cr\u00edtica'],
  ['N\u00e3o dispon\u00edvel', 'N\u00e3o dispon\u00edvel'],
  ['2017 a 2020.xlsx', '2017 a 2020.xlsx'],
  ['per?odo', 'per?odo'],
  ['&amp;atilde;', '&amp;atilde;'],
  ['<script>alert(1)</script>', '<script>alert(1)</script>'],
]

for (const [input, output] of historicalTexts) {
  test(`historical text remains safe: ${input}`, async ({ page }) => {
    let dialogs = 0
    page.on('dialog', async dialog => { dialogs++; await dialog.dismiss() })
    await page.route('**/api/analysis/history', route => route.fulfill({ json: [{
      ...entries[0], arquivos: ['2017 a 2020.xlsx'], status: input,
      quality: { classificacao_qualidade: 'critica' },
    }] }))
    await page.goto('/history')
    await expect(page.getByText(`Status: ${output} \u00b7 Qualidade: Cr\u00edtica`, { exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: '2017 a 2020.xlsx' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Hist\u00f3rico', exact: true })).toBeVisible()
    await expect(page.locator('article script')).toHaveCount(0)
    expect(dialogs).toBe(0)
  })
}
