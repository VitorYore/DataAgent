import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

const report = JSON.parse(readFileSync('../reports/resumo_executivo.json', 'utf8'))

test('API real, CORS e cinco páginas', async ({ page, request }) => {
  const health = await request.get('http://localhost:8000/api/health')
  expect(health.status()).toBe(200)
  expect(await health.json()).toEqual({ status: 'ok', service: 'DataAgent API' })
  for (const [path, title] of [
    ['/', 'Visão geral'], ['/performance', 'Desempenho'], ['/products', 'Produtos'],
    ['/customers', 'Clientes'], ['/opportunities', 'Oportunidades'],
  ]) {
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.message))
    const responsePromise = page.waitForResponse('**/api/analysis/latest')
    await page.goto(path)
    const response = await responsePromise
    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual(report)
    expect(response.headers()['access-control-allow-origin']).toBe('http://127.0.0.1:5173')
    await expect(page.getByRole('heading', { name: title, exact: true }).first()).toBeVisible()
    if (path === '/opportunities' && !report.oportunidades.length && !report.principais_riscos.length && !report.principais_insights.length) {
      await expect(page.getByText('Nenhuma oportunidade para exibir')).toBeVisible()
      await expect(page.getByText('Nenhum ponto de atenção para exibir')).toBeVisible()
      await expect(page.getByText('Nenhum insight para exibir')).toBeVisible()
    } else {
      await expect(page.getByRole('article').first()).toBeVisible()
    }
    await expect(page.getByRole('alert')).toHaveCount(0)
    expect(errors).toEqual([])
  }
})

test('HTTP 404 mostra ausência e permite tentar de novo', async ({ page }) => {
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ status: 404, json: { detail: 'Nenhuma análise disponível.' } }))
  await page.goto('/')
  await expect(page.getByText('Nenhuma análise disponível', { exact: true })).toBeVisible()
  await expect(page.getByRole('article')).toHaveCount(0)
  await page.unroute('**/api/analysis/latest')
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('region', { name: 'KPIs' })).toBeVisible()
})

test('falhas de rede e HTTP não retornam mock', async ({ page }) => {
  await page.route('**/api/analysis/latest', (route) => route.abort('connectionrefused'))
  await page.goto('/products')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('article')).toHaveCount(0)
  await page.unroute('**/api/analysis/latest')
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ status: 500, json: { detail: 'Erro' } }))
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('article')).toHaveCount(0)
  await page.unroute('**/api/analysis/latest')
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('article').first()).toBeVisible()
})
