import { expect, test } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

test('análise demorada não é cancelada por temporizador do frontend', async ({ page }) => {
  await page.goto('/data')
  await expect(page.getByText('Qualidade não disponível', { exact: true })).toBeVisible()
  await page.clock.install()
  let release: () => void = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/analysis', async route => {
    await gate
    await route.fulfill({ json: { status: 'success', summary: resumoExecutivo, files_processed: 1 } })
  })
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'vendas.csv', mimeType: 'text/csv', buffer: Buffer.from('Cliente,Valor\nA,100') })
  await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Analisando dados...' })).toBeDisabled()
  await page.clock.fastForward(300000)
  await expect(page.getByRole('button', { name: 'Analisando dados...' })).toBeDisabled()
  await expect(page.getByRole('alert')).toHaveCount(0)
  release()
  await expect(page).toHaveURL('/')
})

test('erros HTTP JSON ou texto preservam o status e não viram falha de rede', async ({ page }) => {
  await page.goto('/data')
  await expect(page.getByText('Qualidade não disponível', { exact: true })).toBeVisible()
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'vendas.csv', mimeType: 'text/csv', buffer: Buffer.from('Cliente,Valor\nA,100') })
  for (const status of [400, 409, 422, 500]) {
    await page.route('**/api/analysis', route => route.fulfill(status === 500
      ? { status, contentType: 'text/plain', body: 'Internal Server Error' }
      : { status, json: { detail: `Mensagem real ${status}` } }))
    await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText(`HTTP ${status}`)
    await expect(page.getByRole('alert')).not.toContainText('conexão com o backend foi interrompida')
    await expect(page.getByRole('button', { name: 'Analisar Dados', exact: true })).toBeEnabled()
    await page.unroute('**/api/analysis')
  }
})
