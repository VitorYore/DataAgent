import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import type { AnalysisHistoryItem } from '../src/types/dataAgent'

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
    expect(response.headers()['access-control-allow-origin']).toBe(new URL(page.url()).origin)
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


test('real historical JSON reaches the API and DOM without corrupting text', async ({ page }) => {
  const original = readFileSync('../data/analysis_history/index.json', 'utf8')
  const items: AnalysisHistoryItem[] = JSON.parse(original).items
  const responsePromise = page.waitForResponse('**/api/analysis/history')
  await page.goto('/history')
  const response = await responsePromise
  expect(response.status()).toBe(200)
  expect(await response.json()).toEqual(items)
  await expect(page.getByRole('heading', { name: 'Hist\u00f3rico', exact: true })).toBeVisible()
  const list = page.getByRole('region', { name: 'An\u00e1lises conclu\u00eddas', exact: true })
  await expect(list.locator('article')).toHaveCount(items.length)
  const noStatus = items.findIndex(item => !item.status && !item.status_negocio)
  if (noStatus >= 0) {
    await expect(list.locator('article').nth(noStatus)).toContainText('Status: N\u00e3o dispon\u00edvel')
  }
  const text = await list.innerText()
  expect(text).not.toMatch(/&(?:atilde|iacute|aacute|eacute|oacute|ccedil);/)
  expect(text).not.toMatch(/\u00c3[\u0080-\u00bf]|\u00c2[\u0080-\u00bf]/)
  expect(readFileSync('../data/analysis_history/index.json', 'utf8')).toBe(original)
})
