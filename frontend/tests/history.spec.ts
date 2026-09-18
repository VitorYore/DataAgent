import { expect, test } from './fixtures'

const history = [{ id: 'new', data_analise: '2026-09-09T14:32:15Z', arquivos: ['Vendas.csv', 'Produtos.csv'], kpis: { faturamento_total: 150, lucro_total: 60 }, score: 85, status: 'saudavel' }, { id: 'old', arquivos: ['anterior.csv'], kpis: {} }]
const comparison = { status: 'disponivel', metricas: {
  faturamento_total: { atual: 150, anterior: 100, variacao_percentual: 50 },
  margem_lucro: { atual: 93.98, anterior: 95.18, variacao_pontos_percentuais: -1.2 },
} }

for (const width of [1440, 768, 320]) {
  test(`histórico e comparação em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/analysis/history', r => r.fulfill({ json: history }))
    await page.route('**/api/analysis/compare', r => r.fulfill({ json: comparison }))
    await page.goto('/data')
    const table = page.getByRole('region', { name: 'Tabela do histórico' })
    await expect(table.locator('tbody tr').first()).toContainText('Vendas.csv + Produtos.csv')
    await expect(table).toContainText('Saudável')
    await expect(page.getByText('Variação: +50%')).toBeVisible()
    await expect(page.getByText('Variação: -1,2 p.p.')).toBeVisible()
    await expect(page.getByText('Variação: Não disponível').first()).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('histórico vazio é um estado válido', async ({ page }) => {
  await page.goto('/data')
  await expect(page.getByText('Nenhuma análise registrada ainda.', { exact: true })).toBeVisible()
  await expect(page.getByText('Execute uma nova análise para visualizar comparações.', { exact: true })).toBeVisible()
})

test('uma análise não inventa comparação', async ({ page }) => {
  await page.route('**/api/analysis/history', r => r.fulfill({ json: [history[0]] }))
  await page.goto('/data')
  await expect(page.getByRole('region', { name: 'Tabela do histórico' }).locator('tbody tr')).toHaveCount(1)
  await expect(page.getByText('Execute uma nova análise para visualizar comparações.', { exact: true })).toBeVisible()
})

test('erro no histórico permite tentar novamente', async ({ page }) => {
  let failed = true
  await page.route('**/api/analysis/history', r => failed ? r.fulfill({ status: 500, json: { detail: 'Falha' } }) : r.fulfill({ json: history }))
  await page.goto('/data')
  await expect(page.getByRole('alert')).toContainText('500')
  failed = false
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Tabela do histórico' })).toBeVisible()
})
