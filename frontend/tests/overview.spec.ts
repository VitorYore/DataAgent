import { expect, test } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

for (const width of [1440, 768, 320]) {
  test(`Overview em ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Visão geral', exact: true })).toBeVisible()
    await expect(page.getByText('Resumo executivo e visão consolidada do negócio.')).toBeVisible()
    await expect(page.getByText('Área em preparação')).toHaveCount(0)
    await expect(page.getByRole('region', { name: 'Resumo executivo' })).toContainText('35 / 100')
    await expect(page.getByRole('region', { name: 'Resumo executivo' })).toContainText('Crítico')
    for (const reason of resumoExecutivo.status_geral.motivos) await expect(page.getByText(reason, { exact: true })).toBeVisible()
    const kpis = page.getByRole('region', { name: 'KPIs', exact: true })
    await expect(kpis.getByRole('article')).toHaveCount(6)
    for (const value of ['R$ 505.159.249,56', 'R$ 474.743.291,13', 'R$ 30.415.958,43', '93,98%', 'R$ 25.257,96', '20.000']) {
      await expect(kpis).toContainText(value)
    }
    const temporal = page.getByRole('region', { name: 'Desempenho', exact: true })
    await expect(temporal.getByRole('article')).toHaveCount(6)
    for (const value of ['queda', '-6,59%', '2018-07', '2022-10', '42,34%', '-30,23%', '2022-11', '2016-11']) {
      await expect(temporal).toContainText(value)
    }
    for (const finding of [...resumoExecutivo.principais_riscos, ...resumoExecutivo.oportunidades, ...resumoExecutivo.principais_insights]) {
      await expect(page.getByText(finding.mensagem, { exact: true })).toBeVisible()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('overview.png'), fullPage: true })
    expect(errors).toEqual([])
  })
}

test('Overview exibe listas vazias e preserva indicadores zerados', async ({ page }) => {
  const summary = structuredClone(resumoExecutivo)
  summary.principais_riscos = []
  summary.oportunidades = []
  summary.principais_insights = []
  summary.status_geral.motivos = []
  summary.kpis.faturamento_total = 0
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: summary }))
  await page.goto('/')
  await expect(page.getByText('Nenhum risco informado')).toBeVisible()
  await expect(page.getByText('Nenhuma oportunidade informada')).toBeVisible()
  await expect(page.getByText('Nenhum insight informado')).toBeVisible()
  await expect(page.getByText('Nenhum motivo informado na análise.')).toBeVisible()
  await expect(page.getByRole('region', { name: 'KPIs' })).toContainText('R$ 0,00')
})

test('Overview sem resumo', async ({ page }) => {
  await page.route('**/api/analysis/latest', (route) => route.fulfill({ status: 404, json: { detail: 'Nenhuma an?lise dispon?vel' } }))
  await page.goto('/')
  await expect(page.getByText('Nenhuma análise disponível')).toBeVisible()
})

test('Overview carregando e recupera????o ap??s erro', async ({ page }) => {
  await page.route('**/api/analysis/latest', () => new Promise<void>(() => {}))
  await page.goto('/')
  await expect(page.getByRole('status')).toContainText('Carregando')
  await page.unroute('**/api/analysis/latest')
  let calls = 0
  await page.route('**/api/analysis/latest', (route) => ++calls === 1
    ? route.fulfill({ status: 500, json: { detail: 'test' } })
    : route.fulfill({ json: resumoExecutivo }))
  await page.reload()
  await expect(page.getByRole('alert')).toContainText('HTTP 500')
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('region', { name: 'KPIs' })).toBeVisible()
})


test('Overview preserva UTF-8 e sinaliza evolucao com base inicial pequena', async ({ page }) => {
  const summary = structuredClone(resumoExecutivo)
  const period = 'per' + String.fromCharCode(237) + 'odo'
  summary.temporal.metrica_principal = 'lucro'
  summary.temporal.nome_metrica_principal = 'Lucro'
  summary.temporal.evolucao_metrica = null
  summary.temporal.evolucao_faturamento = null
  summary.temporal.evolucao_motivo = 'base_muito_baixa'
  summary.temporal.evolucao_variacao_absoluta = 64213.81
  summary.temporal.tendencia_metrica = undefined
  summary.temporal.tendencia_faturamento = undefined
  summary.principais_insights = [{
    tipo: 'positivo', categoria: 'melhor_periodo', prioridade: 'media',
    mensagem: `O ${period} 2020-10 apresentou o maior valor de Lucro.`,
  }]
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: summary }))
  await page.goto('/')
  await expect(page.getByText(`O ${period} 2020-10 apresentou o maior valor de Lucro.`, { exact: true })).toBeVisible()
  const temporal = page.getByRole('region', { name: 'Desempenho', exact: true })
  await expect(temporal).toContainText('Base inicial muito baixa')
  await expect(temporal).toContainText('+R$ 64.213,81')
  await expect(temporal).not.toContainText('167.006,01%')
})
