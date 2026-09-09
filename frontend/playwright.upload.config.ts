import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'

export default defineConfig({
  testDir: './tests',
  testMatch: '**/upload-flow.spec.ts',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel: 'msedge',
    headless: true,
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: `"${resolve('../.venv/Scripts/python.exe')}" -m uvicorn api.test_upload_server:app --app-dir .. --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/api/health',
    },
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
    },
  ],
})
