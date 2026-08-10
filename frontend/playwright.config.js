import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const isLiveSmoke = process.env.PLAYWRIGHT_LIVE_SMOKE === 'true'
const e2eDatabaseUrl = process.env.DATABASE_URL_E2E || 'postgresql+psycopg://localhost/stock_pattern_project_e2e'
const frontendRoot = fileURLToPath(new URL('.', import.meta.url))
const frontendPort = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 4173)
const frontendUrl = `http://127.0.0.1:${frontendPort}`

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  testIgnore: isLiveSmoke ? [] : ['**/live-smoke.spec.js'],
  use: {
    baseURL: frontendUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  webServer: [
    {
      command: 'node ./scripts/prepare-e2e-db.mjs && python ./scripts/run-e2e-backend.py',
      cwd: frontendRoot,
      url: 'http://127.0.0.1:5010/api/health',
      reuseExistingServer: false,
      timeout: 120 * 1000,
      env: {
        ...process.env,
        APP_ENV: 'test',
        DATABASE_URL: e2eDatabaseUrl,
        DATABASE_URL_E2E: e2eDatabaseUrl,
        MARKET_DATA_PROVIDER: isLiveSmoke ? (process.env.MARKET_DATA_PROVIDER || 'auto') : 'yahoo',
        MARKET_DATA_TIMEOUT_SECONDS: isLiveSmoke ? (process.env.MARKET_DATA_TIMEOUT_SECONDS || '3.5') : '0.2',
        YAHOO_DATA_BASE_URL: isLiveSmoke
          ? (process.env.YAHOO_DATA_BASE_URL || 'https://query1.finance.yahoo.com')
          : 'http://127.0.0.1:9',
        MOCK_DAILY_CANDLE_COUNT: isLiveSmoke ? (process.env.MOCK_DAILY_CANDLE_COUNT || '3200') : '180',
        PERSIST_ANALYSIS_RUNS: 'false',
        USE_MOCK_FALLBACK: 'true',
        STOCK_PATTERN_SNAPSHOT_WARM_ON_START: 'false',
        STOCK_ANALYSIS_CACHE_WARM_ON_START: 'false',
        PERIODIC_CACHE_WARM_ENABLED: 'false',
        MARKET_DATA_TOKEN: isLiveSmoke ? (process.env.MARKET_DATA_TOKEN || '') : '',
        PORT: '5010',
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: frontendRoot,
      url: `${frontendUrl}/`,
      reuseExistingServer: false,
      timeout: 120 * 1000,
      env: {
        ...process.env,
        VITE_API_PROXY_TARGET: 'http://127.0.0.1:5010'
      }
    }
  ],
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome']
      }
    },
    {
      name: 'mobile-chromium',
      use: {
        browserName: 'chromium',
        ...devices['iPhone 13']
      }
    }
  ]
})
