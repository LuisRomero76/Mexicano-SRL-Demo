import { defineConfig, devices } from '@playwright/test'

/**
 * Pruebas de extremo a extremo. Requieren el backend en marcha con los datos de demostración
 * (ver README). Levantan Vite si no está corriendo; si ya lo está, lo reutilizan.
 */
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL,
    locale: 'es-BO',
    timezoneId: 'America/La_Paz',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] }, testMatch: /publico\.spec\.ts/ },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: 'pnpm dev --port 5173 --strictPort', url: baseURL, reuseExistingServer: true, timeout: 60_000 },
})
