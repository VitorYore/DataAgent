import { test, expect } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

const analysisId = 'analysis_20260916_141212123456_0123456789abcdef0123456789abcdef'
const request = {
  status: 'mapping_required', analysis_id: analysisId,
  message: 'Os dados foram estruturados, mas alguns campos precisam ser confirmados.',
  automatic_mappings: { coluna_1: 'data' },
  detected_columns: [
    { nome: 'coluna_1', papel_estrutural: 'data', confianca_estrutural: 0.99, conceito_semantico: 'data', confianca_semantica: 0.99, estado: 'confirmado', exemplos: ['2017-01-02'], percentual_nulos: 0, cardinalidade: 3, conceitos_compativeis: ['data', 'ignorar'] },
    { nome: 'coluna_2', papel_estrutural: 'valor_monetario', confianca_estrutural: 0.99, conceito_semantico: null, confianca_semantica: 0.2, estado: 'desconhecido', exemplos: ['1204.00', '50.00'], percentual_nulos: 0, cardinalidade: 3, conceitos_compativeis: ['faturamento', 'custo', 'outro', 'ignorar'] },
  ],
  required_mappings: [{ coluna: 'coluna_2', conceitos_compativeis: ['faturamento', 'custo', 'outro', 'ignorar'] }],
  concepts: [
    { id: 'data', label: 'Data' },
    { id: 'faturamento', label: 'Faturamento' }, { id: 'custo', label: 'Custo' },
    { id: 'outro', label: 'Outro / dimensão genérica' }, { id: 'ignorar', label: 'Ignorar' },
  ],
}

test('upload ambíguo persiste mapping_required, valida confirmação e atualiza a aplicação', async ({ page }) => {
  let mappingPosts = 0
  const finalSummary = {
    ...resumoExecutivo,
    dados: {
      ...resumoExecutivo.dados,
      mapeamento_semantico: {
        automatico: { coluna_1: 'data' },
        confirmado_pelo_usuario: { coluna_2: 'faturamento' },
      },
    },
  }

  await page.route('**/api/analysis', (route) => route.fulfill({ status: 200, json: request }))
  await page.route(`**/api/analysis/${analysisId}/mapping`, async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ status: 200, json: request })
    mappingPosts += 1
    expect(route.request().postDataJSON()).toEqual({ mappings: { coluna_2: 'faturamento' } })
    if (mappingPosts === 1) return route.fulfill({ status: 422, json: { detail: 'A coluna não passou pela validação semântica.' } })
    return route.fulfill({ status: 200, json: { status: 'success', files_processed: 1, summary: finalSummary } })
  })

  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/data')
  await page.getByLabel('Selecionar arquivos CSV ou Excel').setInputFiles({ name: 'relatorio.xlsx', mimeType: 'application/octet-stream', buffer: Buffer.from('fixture') })
  await page.getByRole('button', { name: 'Analisar Dados', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Confirme alguns campos' })).toBeVisible()
  await expect(page.getByText('Data', { exact: true })).toBeVisible()
  await expect(page.getByText('Valor monetário', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Confirmar e analisar' })).toBeDisabled()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Confirme alguns campos' })).toBeVisible()
  await page.getByLabel('Qual significado descreve este campo?').selectOption('faturamento')
  await expect(page.getByRole('button', { name: 'Confirmar e analisar' })).toBeEnabled()

  await page.getByRole('button', { name: 'Confirmar e analisar' }).click()
  await expect(page.getByRole('alert')).toContainText('A coluna não passou pela validação semântica.')
  await expect(page.getByRole('button', { name: 'Confirmar e analisar' })).toBeEnabled()
  await page.getByRole('button', { name: 'Confirmar e analisar' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('region', { name: 'KPIs', exact: true })).toContainText('R$ 505.159.249,56')
  await page.getByRole('button', { name: 'Abrir navegação' }).click()
  await page.getByRole('link', { name: 'Dados', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Mapeamento utilizado', exact: true })).toContainText('Confirmado pelo usuário')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(await page.locator('body').innerText()).not.toMatch(/[\u{1F300}-\u{1FAFF}]/u)
})




