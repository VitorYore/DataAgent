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
    const revenue = page.getByRole('table', { name: /^Ranking de clientes por faturamento$/i })
    const profit = page.getByRole('table', { name: /^Ranking de clientes por lucro$/i })
    await expect(revenue.locator('tbody tr').first()).toContainText('Mesmo Nome (ID 123)')
    await expect(revenue.locator('tbody tr').first()).toContainText('R$ 400,00')
    await expect(profit.locator('tbody tr').first()).toContainText('Mesmo Nome (ID 456)')
    await expect(profit.locator('tbody tr').first()).toContainText('R$ 200,00')
    await expect(page.getByRole('region', { name: 'Visão da base', exact: true })).toContainText('57,14%')
    await expect(page.getByRole('region', { name: 'Insights da carteira', exact: true })).toContainText(customers.insights_clientes![0])
    await expect(page.getByText(resumoExecutivo.principais_insights[0].mensagem)).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    if (width === 320) {
      const scroll = page.getByRole('region', { name: /^Ranking de clientes por faturamento$/i })
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
    await expect(page.getByRole('heading', { name: /Clientes com .* negativo/i })).toHaveCount(0)
    await page.unroute('**/api/analysis/latest')
  }
})

test('clientes: lucro indisponível não vira zero e não altera a ordem do ranking', async ({ page }) => {
  const partial: CustomerSummary = {
    ...customers,
    clientes_resultado_negativo: null,
    cliente_maior_lucro: undefined,
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
  await expect(page.getByRole('heading', { name: 'Cliente com maior Lucro', exact: true })).toHaveCount(0)
  await expect(page.getByText('Rankings indisponíveis')).toHaveCount(0)
})

test('clientes: usa Valor Total e Margem Bruta sem inventar faturamento ou lucro', async ({ page }) => {
  const semantic: CustomerSummary = {
    quantidade_clientes: 3325,
    metrica_principal: { conceito: 'valor_total', label: 'Valor Total' },
    participacao_maior_cliente_metrica: { conceito: 'valor_total', label: 'Valor Total' },
    concentracao_top_5_metrica: { conceito: 'valor_total', label: 'Valor Total' },
    participacao_maior_cliente: 7.47,
    concentracao_top_5: 22.28,
    rankings: {
      valor_total: { conceito: 'valor_total', label: 'Valor Total', items: [{ posicao: 1, cliente: 'MINERAÇÃO CAIEIRAS', valor: 632033.34, conceito: 'valor_total' }] },
      margem_bruta: { conceito: 'margem_bruta', label: 'Margem Bruta', items: [{ posicao: 1, cliente: 'MINERAÇÃO CAIEIRAS', valor: 200328.52, conceito: 'margem_bruta' }] },
    },
    cliente_maior_valor_total: { cliente: 'MINERAÇÃO CAIEIRAS', valor_total: 632033.34 },
    cliente_maior_margem_bruta: { cliente: 'MINERAÇÃO CAIEIRAS', margem_bruta: 200328.52 },
    clientes_metrica_negativa: { conceito: 'margem_bruta', label: 'Margem Bruta', quantidade: 3 },
  }
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: { ...resumoExecutivo, clientes: semantic } }))
  await page.goto('/customers')
  await expect(page.getByRole('heading', { name: 'Cliente com maior Valor Total', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Cliente com maior Margem Bruta', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Clientes com Margem Bruta negativa', exact: true })).toBeVisible()
  await expect(page.getByText('do Valor Total')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Cliente com maior Faturamento', exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Cliente com maior Lucro', exact: true })).toHaveCount(0)
})


test('clientes: ranking semantico nao oculta ranking legado de outra metrica', async ({ page }) => {
  const mixed: CustomerSummary = {
    ...customers,
    rankings: {
      lucro: { conceito: 'lucro', label: 'Lucro', items: [{ posicao: 1, cliente: 'Cliente lucro', valor: 200, conceito: 'lucro' }] },
    },
    ranking_faturamento: [
      { posicao: 1, cliente: 'Cliente faturamento', faturamento: 400, lucro: null },
    ],
  }
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: { ...resumoExecutivo, clientes: mixed } }))
  await page.goto('/customers')
  await expect(page.getByRole('table', { name: /^Ranking de clientes por Faturamento$/i })).toContainText('Cliente faturamento')
  await expect(page.getByRole('table', { name: /^Ranking de clientes por Lucro$/i })).toContainText('Cliente lucro')
})
