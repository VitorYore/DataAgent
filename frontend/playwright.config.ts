import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'

export default defineConfig({
  testDir: './tests',
  testIgnore: '**/upload-flow.spec.ts',
  fullyParallel: true,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel: 'msedge',
    headless: true,
    screenshot: 'only-on-failure',
  },
  webServer: [{
    command: `"${resolve('../.venv/Scripts/python.exe')}" -m uvicorn api.app:app --app-dir .. --host 127.0.0.1 --port 8000`,
    url: 'http://127.0.0.1:8000/api/health',
    reuseExistingServer: false,
  }, {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
  }],
})
