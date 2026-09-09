import { expect, test } from './fixtures'

for (const width of [1440, 768, 320]) {
  test(`oportunidades: filtros em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/opportunities')
    await expect(page.getByRole('article')).toHaveCount(3)
    await expect(page.getByRole('heading', { name: 'Pontos de Atenção' })).toBeVisible()
    await expect(page.getByText('Tipo: atencao', { exact: true })).toBeVisible()
    await page.getByLabel('Prioridade', { exact: true }).selectOption('alta')
    await expect(page.getByRole('article')).toHaveCount(2)
    await expect(page.getByText('Nenhuma oportunidade para exibir')).toBeVisible()
    await page.getByLabel('Categoria', { exact: true }).selectOption('crescimento')
    await expect(page.getByRole('article')).toHaveCount(1)
    await expect(page.getByRole('article')).toContainText('A maior queda mensal ocorreu em 2016-11, com redução de 30.23%.')
    await page.getByLabel('Prioridade', { exact: true }).selectOption('media')
    await expect(page.getByRole('article')).toHaveCount(0)
    await page.getByLabel('Categoria', { exact: true }).selectOption('produto')
    await expect(page.getByRole('article')).toHaveCount(1)
    await expect(page.getByRole('article')).toContainText("O produto 'Officia (ID 724)'")
    await page.getByLabel('Prioridade', { exact: true }).selectOption('')
    await page.getByLabel('Categoria', { exact: true }).selectOption('')
    await expect(page.getByRole('article')).toHaveCount(3)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })

  test(`dados: seleção local em ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    const posts: string[] = []
    page.on('request', (request) => { if (request.method() === 'POST') posts.push(request.url()) })
    await page.goto('/data')
    await expect(page.getByRole('button', { name: 'Analisar Dados' })).toBeDisabled()
    await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles([
      { name: 'vendas.csv', mimeType: 'text/csv', buffer: Buffer.from('a,b\n1,2') },
      { name: 'clientes.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('local only') },
      { name: 'estoque.xls', mimeType: 'application/vnd.ms-excel', buffer: Buffer.from('local only') },
    ])
    await expect(page.getByText('Quantidade de arquivos selecionados: 3')).toBeVisible()
    await expect(page.getByText('7 bytes', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Remover clientes.xlsx' }).click()
    await expect(page.getByText('Quantidade de arquivos selecionados: 2')).toBeVisible()
    await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles([
      { name: 'arquivo.txt', mimeType: 'text/plain', buffer: Buffer.from('invalid') },
    ])
    await expect(page.getByRole('alert')).toContainText('Selecione apenas CSV, XLS ou XLSX.')
    await expect(page.getByText('Quantidade de arquivos selecionados: 2')).toBeVisible()
    const transfer = await page.evaluateHandle(() => {
      const data = new DataTransfer()
      data.items.add(new File(['a,b'], 'nome-muito-longo-de-arquivo-para-verificar-responsividade-dos-datasets.CSV', { type: 'text/csv' }))
      return data
    })
    await page.getByText('Arraste seus arquivos para esta área').dispatchEvent('drop', { dataTransfer: transfer })
    await transfer.dispose()
    await expect(page.getByText('Quantidade de arquivos selecionados: 3')).toBeVisible()
    await page.route('**/api/analysis', (route) => route.fulfill({ status: 422, json: { detail: 'Não foi possível ler os arquivos enviados.' } }))
    await page.getByRole('button', { name: 'Analisar Dados' }).click()
    await expect(page.getByRole('alert')).toContainText('Não foi possível ler os arquivos enviados.')
    expect(posts).toHaveLength(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('data.png'), fullPage: true })
    await page.reload()
    await expect(page.getByText('Quantidade de arquivos selecionados: 0')).toBeVisible()
  })
}
