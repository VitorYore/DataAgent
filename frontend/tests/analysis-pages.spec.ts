import { expect, test } from './fixtures'

const pages = [
  { path: '/performance', title: 'Desempenho', cards: 13 },
  { path: '/products', title: 'Produtos', cards: 6 },
  { path: '/customers', title: 'Clientes', cards: 5 },
]
const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
  { name: 'mobile-small', width: 320, height: 740 },
]

for (const viewport of viewports) {
  for (const item of pages) {
    test(`${item.title} em ${viewport.name}`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport)
      const errors: string[] = []
      page.on('pageerror', (error) => errors.push(error.message))
      await page.goto(item.path)
      await expect(page.getByRole('heading', { name: item.title, exact: true })).toBeVisible()
      await expect(page.locator('article')).toHaveCount(item.cards)
      const card = (title: string) => page.getByRole('article').filter({
        has: page.getByRole('heading', { name: title, exact: true }),
      })
      if (item.path === '/performance') {
        for (const [title, value] of [
          ['Faturamento', 'R$ 505.159.249,56'], ['Lucro', 'R$ 474.743.291,13'],
          ['Custo', 'R$ 30.415.958,43'], ['Margem de lucro', '93,98%'],
          ['Ticket médio', 'R$ 25.257,96'], ['Pedidos', '20.000'],
          ['Quantidade vendida', '1.009.021'], ['Tendência de faturamento', 'queda'],
          ['Evolução do faturamento', '-6,59%'], ['Melhor período', '2018-07'],
          ['Pior período', '2022-10'], ['Maior crescimento', '42,34%'],
          ['Maior queda', '-30,23%'],
        ]) await expect(card(title)).toContainText(value)
        await expect(card('Melhor período')).toContainText('R$ 5.115.750,38')
        await expect(card('Pior período')).toContainText('R$ 2.890.558,57')
        await expect(card('Maior crescimento')).toContainText('2022-11')
        await expect(card('Maior queda')).toContainText('2016-11')
        await expect(page.getByLabel('Gráfico de faturamento e lucro')).toBeVisible()
      } else if (item.path === '/products') {
        await expect(card('Quantidade de produtos')).toContainText('1.000')
        await expect(card('Produto mais vendido')).toContainText('Molestias (ID 425)')
        await expect(card('Produto mais vendido')).toContainText('1.935')
        await expect(card('Produto com maior faturamento')).toContainText('Quis (ID 541)')
        await expect(card('Produto com maior faturamento')).toContainText('R$ 952.866,23')
        await expect(card('Produto com maior lucro')).toContainText('R$ 921.997,03')
        await expect(card('Produtos em risco de ruptura').locator('p')).toHaveText('0')
        await expect(card('Produtos com estoque excessivo').locator('p')).toHaveText('0')
        await expect(page.getByRole('table')).toBeVisible()
      } else {
        await expect(card('Quantidade de clientes')).toContainText('1.000')
        await expect(card('Cliente com maior faturamento')).toContainText('Kyara Santos (ID 874)')
        await expect(card('Cliente com maior faturamento')).toContainText('R$ 1.086.012,31')
        await expect(card('Cliente com maior lucro')).toContainText('R$ 1.023.409,47')
        await expect(page.getByRole('meter')).toHaveAttribute('aria-valuenow', '1.03')
        await expect(page.getByRole('meter')).toHaveAttribute('aria-valuetext', '1,03%')
        await expect(page.getByRole('meter').locator('div')).toHaveAttribute('style', 'width: 1.03%;')
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      // Check individual cards as well: overflow-hidden must not conceal clipped content.
      for (const article of await page.locator('article').all()) {
        expect(await article.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
      }
      await page.screenshot({ path: testInfo.outputPath('page.png'), fullPage: true })
      if (viewport.width < 768) await page.getByRole('button', { name: 'Abrir navegação' }).click()
      await page.getByRole('link', { name: 'Produtos', exact: true }).click()
      await expect(page).toHaveURL('/products')
      if (viewport.width < 768) await expect(page.getByRole('button', { name: 'Abrir navegação' })).toHaveAttribute('aria-expanded', 'false')
      expect(errors).toEqual([])
    })
  }
}

test('carregamento e recuperação de erro do serviço', async ({ page }) => {
  await page.route('**/src/services/dataAgentService.ts', (route) => route.fulfill({
    contentType: 'application/javascript',
    body: 'export async function analyzeDatasets() { throw new Error("Unavailable") } export function getExecutiveSummary() { return new Promise(() => {}) }',
  }))
  await page.goto('/performance')
  await expect(page.getByRole('status')).toContainText('Carregando análise')
  await page.unroute('**/src/services/dataAgentService.ts')
  await page.route('**/src/services/dataAgentService.ts', (route) => route.fulfill({
    contentType: 'application/javascript',
    body: 'export async function analyzeDatasets() { throw new Error("Unavailable") } let calls = 0; export async function getExecutiveSummary() { if (++calls <= 1) throw new Error("test"); const { resumoExecutivo } = await import("/src/mocks/resumoExecutivo.ts"); return structuredClone(resumoExecutivo) }',
  }))
  await page.reload()
  await expect(page.getByRole('alert')).toContainText('Não foi possível carregar a análise')
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.locator('article')).toHaveCount(13)
})
