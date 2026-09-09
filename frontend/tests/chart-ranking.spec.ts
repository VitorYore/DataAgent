import { expect, test } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

test('gráfico usa os pontos do serviço e mostra tooltip monetário sem warnings', async ({ page }) => {
  const problems: string[] = []
  page.on('console', (message) => { if (['warning', 'error'].includes(message.type())) problems.push(message.text()) })
  page.on('pageerror', (error) => problems.push(error.message))
  await page.goto('/performance')
  const chart = page.getByLabel('Gráfico de faturamento e lucro')
  await expect(chart.locator('.recharts-line')).toHaveCount(2)
  await expect(chart.locator('.recharts-line-dot')).toHaveCount(4)
  await expect(page.getByText('Histórico ainda indisponível')).toHaveCount(0)
  await chart.locator('.recharts-line-dot').first().hover({ force: true })
  await expect(chart.locator('.recharts-tooltip-wrapper')).toContainText('R$ 4.123.456,78')
  await expect(chart.locator('.recharts-tooltip-wrapper')).toContainText('R$ 3.890.000,12')
  expect(problems).toEqual([])
})

test('listas vazias usam os estados originais', async ({ page }) => {
  const summary = structuredClone(resumoExecutivo)
  summary.temporal.serie_temporal = []
  summary.produtos.ranking_produtos = []
  await page.route('**/src/services/dataAgentService.ts', (route) => route.fulfill({
    contentType: 'application/javascript',
    body: `export async function analyzeDatasets() {} export async function getExecutiveSummary() { return ${JSON.stringify(summary)} }`,
  }))
  await page.goto('/performance')
  await expect(page.getByText('Histórico ainda indisponível')).toBeVisible()
  await expect(page.getByLabel('Gráfico de faturamento e lucro')).toHaveCount(0)
  await page.goto('/products')
  await expect(page.getByText('Rankings ainda indisponíveis')).toBeVisible()
  await expect(page.getByRole('table')).toHaveCount(0)
})

test('nulos não viram zero e posições não são recalculadas', async ({ page }) => {
  const summary = structuredClone(resumoExecutivo)
  summary.temporal.serie_temporal = [
    { periodo: '2015-01', faturamento: 0, lucro: null },
    { periodo: '2015-02', lucro: 3770000 },
  ]
  summary.produtos.ranking_produtos = [
    { ...summary.produtos.ranking_produtos[0], posicao: 7, avaliacao_media: null, taxa_devolucao: null, estoque_atual: 0 },
    { ...summary.produtos.ranking_produtos[0], posicao: 2, produto: 'Segundo item recebido' },
  ]
  await page.route('**/src/services/dataAgentService.ts', (route) => route.fulfill({
    contentType: 'application/javascript',
    body: `export async function analyzeDatasets() {} export async function getExecutiveSummary() { return ${JSON.stringify(summary)} }`,
  }))
  await page.goto('/performance')
  await expect(page.getByLabel('Gráfico de faturamento e lucro').locator('.recharts-line-dot')).toHaveCount(2)
  await page.goto('/products')
  const rows = page.getByRole('table').locator('tbody tr')
  await expect(rows).toHaveCount(2)
  await expect(rows.first().locator('td').first()).toHaveText('7')
  await expect(rows.nth(1).locator('td').first()).toHaveText('2')
  await expect(rows.first().getByText('Não disponível', { exact: true })).toHaveCount(2)
  await expect(rows.first().locator('td').nth(5)).toHaveText('0')
})
