import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

const csv = 'pedido_id,data,produto,cliente,quantidade,preco_unitario,custo_unitario\n1,2025-01-15,Produto A,Cliente A,2,100,30\n2,2025-02-15,Produto B,Cliente B,3,200,50\n3,2025-03-15,Produto A,Cliente A,1,100,30\n'

test('Excel complexo normaliza antes de analisar e apresenta auditoria na página Dados', async ({ page }) => {
  const encoded = execFileSync(resolve('../.venv/Scripts/python.exe'), ['-c', `import pandas as pd, io, base64
b=io.BytesIO()
pd.DataFrame([['Pedido_ID','Data','Faturamento','Lucro'],['Janeiro'],[1,'2025-01-01',100,40],[2,'2025-01-02',200,50],['Total',None,300,90]]).to_excel(b,index=False,header=False)
print(base64.b64encode(b.getvalue()).decode())`], { encoding: 'utf8' })
  await page.goto('/data')
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'relatorio.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from(encoded.trim(), 'base64') })
  const response = page.waitForResponse(r => r.url().endsWith('/api/analysis') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
  const result = await response
  expect(result.status()).toBe(200)
  const summary = (await result.json()).summary
  expect(summary.kpis.faturamento_total).toBe(300)
  expect(summary.dados.ingestao.normalizacao.registros_extraidos).toBe(2)
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText('R$ 300,00')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  await expect(page.getByText('Relatório operacional normalizado', { exact: true })).toBeVisible()
})

test('duas análises reais atualizam histórico e comparação sem reload', async ({ page }) => {
  for (const [name, contents] of [['primeira.csv', csv], ['segunda.csv', csv.replace('2,100,30', '2,200,30')]]) {
    await page.goto('/data')
    await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name, mimeType: 'text/csv', buffer: Buffer.from(contents) })
    const completed = page.waitForResponse(r => r.url().endsWith('/api/analysis') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
    expect((await completed).status()).toBe(200)
    await expect(page).toHaveURL('/')
    await page.getByRole('link', { name: 'Dados', exact: true }).click()
    await expect(page.getByRole('region', { name: 'Tabela do histórico' }).locator('tbody tr').first()).toContainText(name)
  }
  await expect(page.getByText('Variação: +22,22%').first()).toBeVisible()
  await expect(page.getByRole('region', { name: 'Qualidade dos dados', exact: true })).toBeVisible()
})

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

test('diagnostico de entidades no upload preserva clientes e historico', async ({ page }) => {
  await page.goto('/data')
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({
    name: 'entidades.csv', mimeType: 'text/csv',
    buffer: Buffer.from('Pedido,Data,Cliente,Valor_Total\n1,2020-01-01,Empresa ABC,100\n2,2020-02-01,EMPRESA ABC,50\n'),
  })
  const uploaded = page.waitForResponse(r => r.url().endsWith('/api/analysis') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
  const response = await uploaded
  expect(response.status()).toBe(200)
  const summary = (await response.json()).summary
  expect(summary.clientes.quantidade_clientes).toBe(2)
  expect(summary.kpis.valor_total).toBe(150)
  expect(summary.dados.entity_resolution.total_candidates).toBe(1)
  await expect(page).toHaveURL('/')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
  await expect(panel).toContainText('Nenhum dado foi alterado.')
  await expect(panel).toContainText('Possível total combinado (Valor Total): R$ 150,00')
  await expect(panel.getByRole('button', { name: 'Unir entidades', exact: true })).toHaveCount(1)
  await page.getByRole('link', { name: 'Histórico', exact: true }).click()
  await page.locator('article').filter({ has: page.getByRole('heading', { name: 'entidades.csv', exact: true }) }).getByRole('button', { name: 'Abrir análise' }).click()
  await expect(page).toHaveURL('/')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  await page.reload()
  await expect(panel).toContainText('Possível total combinado (Valor Total): R$ 150,00')
})

test('uniao real preserva totais e reaparece no historico', async ({ page }) => {
  await page.goto('/data')
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({
    name: 'uniao.csv', mimeType: 'text/csv',
    buffer: Buffer.from('Pedido,Data,Cliente,Faturamento,Custo,Lucro\n1,2020-01-01,Empresa ABC,100,70,30\n2,2020-02-01,EMPRESA ABC,50,30,20\n'),
  })
  const uploaded = page.waitForResponse(r => r.url().endsWith('/api/analysis') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
  const before = (await (await uploaded).json()).summary
  await expect(page).toHaveURL('/')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  const panel = page.getByRole('region', { name: 'Possíveis duplicidades' })
  await panel.getByRole('button', { name: 'Unir entidades', exact: true }).click()
  const confirmed = page.waitForResponse(r => r.url().endsWith('/entities') && r.request().method() === 'POST')
  await panel.getByRole('button', { name: 'Confirmar união', exact: true }).click()
  const response = await confirmed
  expect(response.status()).toBe(200)
  const after = (await response.json()).summary
  expect(after.kpis).toEqual(before.kpis)
  expect(after.temporal).toEqual(before.temporal)
  expect(before.clientes.quantidade_clientes).toBe(2)
  expect(after.clientes.quantidade_clientes).toBe(1)
  await panel.getByLabel('Estado das sugestões').selectOption('merged')
  await expect(panel).toContainText('Label utilizado: Empresa ABC')
  await page.getByRole('link', { name: 'Clientes', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Clientes', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Histórico', exact: true }).click()
  await page.locator('article').filter({ has: page.getByRole('heading', { name: 'uniao.csv', exact: true }) }).getByRole('button', { name: 'Abrir análise' }).click()
  await expect(page).toHaveURL('/')
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  await page.reload()
  await panel.getByLabel('Estado das sugestões').selectOption('merged')
  await expect(panel).toContainText('Label utilizado: Empresa ABC')
})
