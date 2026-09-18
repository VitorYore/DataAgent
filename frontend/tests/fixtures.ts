// Somente testes isolados interceptam a API. A aplicação não importa este arquivo.
import { test as base, expect } from '@playwright/test'
import { resumoExecutivo } from '../src/mocks/resumoExecutivo'

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route('**/api/analysis/latest', (route) => route.fulfill({ json: resumoExecutivo }))
    await page.route('**/api/analysis/history', (route) => route.fulfill({ json: [] }))
    await page.route('**/api/analysis/compare', (route) => route.fulfill({ json: { status: 'insuficiente', metricas: {} } }))
    await use(page)
  },
})
export { expect }
