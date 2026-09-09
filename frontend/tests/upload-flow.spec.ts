import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

const csv = 'pedido_id,data,produto,cliente,quantidade,preco_unitario,custo_unitario\n1,2025-01-15,Produto A,Cliente A,2,100,30\n2,2025-02-15,Produto B,Cliente B,3,200,50\n3,2025-03-15,Produto A,Cliente A,1,100,30\n'

test('GET antigo não sobrescreve o resultado novo do upload', async ({ page }) => {
  let release: () => void = () => {}
  const gate = new Promise<void>((resolve) => { release = resolve })
  await page.route('**/api/analysis/latest', async (route) => {
    await gate
    await route.fulfill({ status: 404, json: { detail: 'Nenhuma análise disponível.' } })
  })
  await page.goto('/')
  await expect(page.getByRole('status')).toContainText('Carregando análise')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'vendas.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
  await page.getByRole('button', { name: 'Analisar Dados' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText('R$ 900,00')
  const stale = page.waitForResponse('**/api/analysis/latest')
  release()
  await (await stale).finished()
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))))
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText('R$ 900,00')
})

test('upload real, loading, atualização global sem GET adicional e preservação em erro', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  const initialSummary = page.waitForResponse('**/api/analysis/latest')
  await page.goto('/data')
  await initialSummary
  let gets = 0
  page.on('request', (request) => { if (request.url().endsWith('/api/analysis/latest')) gets++ })
  await page.evaluate(() => { document.body.dataset.session = 'same-page' })
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'vendas.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
  let release: () => void = () => {}
  const gate = new Promise<void>((resolve) => { release = resolve })
  await page.route('**/api/analysis', async (route) => { await gate; await route.continue() })
  const result = page.waitForResponse((response) => response.url().endsWith('/api/analysis') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Analisar Dados' }).click()
  await expect(page.getByRole('button', { name: 'Analisando dados...' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Remover vendas.csv' })).toBeDisabled()
  release()
  expect((await result).status()).toBe(200)
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText('R$ 900,00')
  for (const label of ['Desempenho', 'Produtos', 'Clientes', 'Oportunidades']) {
    await page.getByRole('link', { name: label, exact: true }).click()
    await expect(page.getByRole('heading', { name: label, exact: true }).first()).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0)
  }
  expect(gets).toBe(0)
  expect(await page.locator('body').getAttribute('data-session')).toBe('same-page')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Qualidade dos dados', exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Arquivos analisados', exact: true })).toContainText('vendas.csv')
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'invalido.xlsx', mimeType: 'application/octet-stream', buffer: Buffer.from('broken excel') })
  await page.getByRole('button', { name: 'Analisar Dados' }).click()
  await expect(page.getByRole('alert')).toContainText('Os dados não puderam ser processados')
  await expect(page.getByText('invalido.xlsx', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Analisar Dados' })).toBeEnabled()
  await page.getByRole('link', { name: 'Visão geral' }).click()
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText('R$ 900,00')
  expect(errors).toEqual([])
})

test('multitabela envia todos os arquivos e disponibiliza o mesmo resultado nas páginas', async ({ page }) => {
  const files = ['Historico_Vendas.csv', 'Clientes.csv', 'Produtos.csv'].map((name) => ({
    name,
    mimeType: 'text/csv',
    buffer: Buffer.from(readFileSync('../data/samples/' + name, 'utf8').split(/\r?\n/).slice(0, name === 'Historico_Vendas.csv' ? 41 : 1001).join('\n')),
  }))
  await page.goto('/data')
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles(files)
  await expect(page.getByText('Quantidade de arquivos selecionados: 3')).toBeVisible()
  const response = page.waitForResponse((item) => item.url().endsWith('/api/analysis') && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Analisar Dados' }).click()
  const result = await response
  expect(result.status()).toBe(200)
  const body = await result.json()
  expect(body.files_processed).toBe(3)
  await expect(page).toHaveURL('/')
  const revenue = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(body.summary.kpis.faturamento_total)
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText(revenue)
  await page.getByRole('link', { name: 'Desempenho', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Indicadores de desempenho' })).toContainText(revenue)
  await page.getByRole('link', { name: 'Produtos', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Portfólio e estoque' })).toContainText(String(body.summary.produtos.quantidade_produtos))
  await page.getByRole('link', { name: 'Clientes', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Visão da base' })).toContainText(String(body.summary.clientes.quantidade_clientes))
  await page.getByRole('link', { name: 'Oportunidades', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Pontos de Atenção' })).toBeVisible()
})
