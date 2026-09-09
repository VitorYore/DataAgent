import { expect, test } from '@playwright/test'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'
import type { CustomerSummary } from '../src/types/dataAgent'

// Fixtures exclusivas de teste. A página recebe tudo pela API, sem fallback.
const customers: CustomerSummary = {
  quantidade_clientes: 3,
  cliente_maior_faturamento: { cliente: 'Mesmo Nome (ID 123)', faturamento: 400 },
  cliente_maior_lucro: { cliente: 'Mesmo Nome (ID 456)', lucro: 200 },
  concentracao_top_5: 100,
  participacao_maior_cliente: 57.14,
  clientes_resultado_negativo: 1,
  ranking_faturamento: [
    { posicao: 1, cliente: 'Mesmo Nome (ID 123)', cliente_id: '123', faturamento: 400, lucro: 100 },
    { posicao: 2, cliente: 'Mesmo Nome (ID 456)', cliente_id: '456', faturamento: 200, lucro: 200 },
  ],
  ranking_lucro: [
    { posicao: 1, cliente: 'Mesmo Nome (ID 456)', cliente_id: '456', lucro: 200, faturamento: 200 },
    { posicao: 2, cliente: 'Mesmo Nome (ID 123)', cliente_id: '123', lucro: 100, faturamento: 400 },
  ],
  insights_clientes: ['Existe 1 cliente com resultado agregado negativo.'],
}

for (const width of [1440, 768, 320]) {
  test(`clientes: rankings e insights em ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.message))
    await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: { ...resumoExecutivo, clientes: customers } }))
    await page.goto('/customers')
    const revenue = page.getByRole('table', { name: 'Ranking de clientes por faturamento', exact: true })
    const profit = page.getByRole('table', { name: 'Ranking de clientes por lucro', exact: true })
    await expect(revenue.locator('tbody tr').first()).toContainText('Mesmo Nome (ID 123)')
    await expect(revenue.locator('tbody tr').first()).toContainText('R$ 400,00')
    await expect(profit.locator('tbody tr').first()).toContainText('Mesmo Nome (ID 456)')
    await expect(profit.locator('tbody tr').first()).toContainText('R$ 200,00')
    await expect(page.getByRole('region', { name: 'Visão da base', exact: true })).toContainText('57,14%')
    await expect(page.getByRole('region', { name: 'Insights da carteira', exact: true })).toContainText(customers.insights_clientes![0])
    await expect(page.getByText(resumoExecutivo.principais_insights[0].mensagem)).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    if (width === 320) {
      const scroll = page.getByRole('region', { name: 'Ranking de clientes por faturamento', exact: true })
      expect(await scroll.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true)
      await scroll.evaluate((element) => { element.scrollLeft = element.scrollWidth })
    }
    await page.screenshot({ path: testInfo.outputPath('customers.png'), fullPage: true })
    expect(errors).toEqual([])
  })
}

test('clientes: relatório antigo e bloco vazio permanecem seguros', async ({ page }) => {
  for (const oldCustomers of [resumoExecutivo.clientes, {}]) {
    await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: { ...resumoExecutivo, clientes: oldCustomers } }))
    await page.goto('/customers')
    await expect(page.getByText('Ranking por faturamento indisponível')).toBeVisible()
    await expect(page.getByText('Ranking por lucro indisponível')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Insights da carteira' })).toHaveCount(0)
    const newCard = page.getByRole('article').filter({ has: page.getByRole('heading', { name: 'Clientes com resultado negativo', exact: true }) })
    await expect(newCard).toContainText('Não disponível')
    await page.unroute('**/api/analysis/latest')
  }
})

test('clientes: lucro indisponível não vira zero e não altera a ordem do ranking', async ({ page }) => {
  const partial: CustomerSummary = {
    ...customers,
    clientes_resultado_negativo: null,
    ranking_lucro: [],
    ranking_faturamento: [
      { posicao: 7, cliente: 'Cliente recebido', faturamento: 130, lucro: null },
      { posicao: 2, cliente: 'Outro cliente recebido', faturamento: 200, lucro: null },
    ],
    insights_clientes: [],
  }
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: { ...resumoExecutivo, clientes: partial } }))
  await page.goto('/customers')
  const rows = page.getByRole('table').locator('tbody tr')
  await expect(rows.first().locator('td').first()).toHaveText('7')
  await expect(rows.first()).toContainText('Não disponível')
  await expect(page.getByText('Ranking por lucro indisponível')).toBeVisible()
})
