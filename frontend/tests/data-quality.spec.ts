import { expect, test } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'
import type { DataQuality } from '../src/types/dataAgent'

const quality: DataQuality = {
  arquivos: [{ nome: 'vendas.csv', linhas: 100, colunas: 4 }], quantidade_arquivos: 1,
  quantidade_linhas: 100, quantidade_colunas: 4, status: 'concluida',
  total_valores_nulos: 4, percentual_nulos_geral: 1, linhas_duplicadas: 2,
  quantidade_problemas: 2, score_qualidade: 92, classificacao_qualidade: 'excelente',
  problemas: [{ nivel: 'baixa', coluna: 'Lucro', mensagem: 'Nulos encontrados.' }, { nivel: 'alta', mensagem: 'Problema relevante.' }],
  transformacoes: [{ coluna: 'Data', antes: 'str', depois: 'datetime64[ns]', descricao: 'Conversão de tipo.' }],
  ingestao: { arquivo: 'vendas.csv', cabecalho_detectado: true, linha_cabecalho: 1, confianca_cabecalho: 95, linhas_vazias_removidas: 0, colunas_vazias_removidas: 0 },
}

for (const width of [1440, 768, 320]) {
  test(`qualidade completa em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/analysis/latest', r => r.fulfill({ json: { ...resumoExecutivo, dados: quality } }))
    await page.goto('/data')
    await expect(page.getByRole('meter', { name: 'Score de qualidade' })).toHaveAttribute('aria-valuenow', '92')
    await expect(page.getByText('Análise concluída', { exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Problemas encontrados', exact: true }).locator('li').first()).toContainText('Problema relevante.')
    await expect(page.getByText('Conversão de tipo.')).toBeVisible()
    await expect(page.getByText('Cabeçalho detectado', { exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(page.getByRole('button', { name: 'Analisar Dados', exact: true })).toBeDisabled()
  })
}

test('análise antiga e listas vazias sem inventar valores', async ({ page }) => {
  await page.goto('/data')
  await expect(page.getByText('Qualidade não disponível', { exact: true })).toBeVisible()
  await page.route('**/api/analysis/latest', r => r.fulfill({ json: { ...resumoExecutivo, dados: { ...quality, problemas: [], transformacoes: [], quantidade_problemas: 0, ingestao: {} } } }))
  await page.reload()
  await expect(page.getByText('Nenhum problema encontrado', { exact: true })).toBeVisible()
  await expect(page.getByText('Nenhuma transformação realizada', { exact: true })).toBeVisible()
  await expect(page.getByText('Ingestão não informada', { exact: true })).toBeVisible()
})

test('multitabela e aviso de cabeçalho ausente', async ({ page }) => {
  await page.route('**/api/analysis/latest', r => r.fulfill({ json: { ...resumoExecutivo, dados: {
    ...quality, quantidade_arquivos: 2,
    arquivos: [...quality.arquivos!, { nome: 'clientes.xlsx', linhas: 20, colunas: 3 }],
    ingestao: { vendas: quality.ingestao, clientes: { arquivo: 'clientes.xlsx', cabecalho_detectado: false, colunas_renomeadas: [{ posicao: 1, original: '', novo: 'coluna_1' }], colunas_muitos_nulos: { coluna_3: 98 } } },
  } } }))
  await page.goto('/data')
  await expect(page.getByRole('region', { name: 'Arquivos analisados', exact: true }).locator('li')).toHaveCount(2)
  await expect(page.getByText('Colunas genéricas utilizadas.', { exact: false })).toBeVisible()
  await expect(page.getByText('coluna_3: 98% de nulos')).toBeVisible()
})
