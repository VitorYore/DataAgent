import { expect, test } from './fixtures'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

test('listas exclusivas, labels amigáveis e filtro pela chave original', async ({ page }) => {
  await page.route('**/api/analysis/latest', route => route.fulfill({ json: {
    ...resumoExecutivo,
    principais_riscos: [{ categoria: 'maior_queda', prioridade: 'alta', mensagem: 'Queda identificada.' }],
    oportunidades: [],
    principais_insights: [{ categoria: 'cliente_destaque', tipo: 'positivo', prioridade: 'media', mensagem: 'Cliente em destaque na carteira.' }],
  } }))
  await page.goto('/opportunities')
  const risks = page.getByRole('region', { name: 'Pontos de Atenção', exact: true })
  const insights = page.getByRole('region', { name: 'Insights', exact: true })
  await expect(risks.getByRole('article')).toHaveCount(1)
  await expect(insights.getByRole('article')).toHaveCount(1)
  await expect(risks).not.toContainText('Cliente em destaque na carteira.')
  await expect(insights).not.toContainText('Queda identificada.')
  await expect(risks).toContainText('Categoria: Maior queda')
  await expect(page.getByText('Nenhuma oportunidade para exibir')).toBeVisible()
  await page.getByLabel('Categoria', { exact: true }).selectOption({ label: 'Maior queda' })
  await expect(page.getByLabel('Categoria', { exact: true })).toHaveValue('maior_queda')
  await expect(risks.getByRole('article')).toHaveCount(1)
  await expect(insights.getByRole('article')).toHaveCount(0)
})
