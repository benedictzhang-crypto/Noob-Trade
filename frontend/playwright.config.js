import { defineConfig, devices } from '@playwright/test'

const isLiveSmoke = process.env.PLAYWRIGHT_LIVE_SMOKE === 'true'
const e2eDatabaseUrl = process.env.DATABASE_URL_E2E || 'postgresql+psycopg://localhost/stock_pattern_project_e2e'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  testIgnore: isLiveSmoke ? [] : ['**/live-smoke.spec.js'],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  webServer: [
    {
      command: 'node ./scripts/prepare-e2e-db.mjs && python ./scripts/run-e2e-backend.py',
      cwd: '/Users/samuel/Documents/stock_pattern_project/frontend',
      url: 'http://127.0.0.1:5010/api/health',
      reuseExistingServer: false,
      timeout: 120 * 1000,
      env: {
        ...process.env,
        DATABASE_URL: e2eDatabaseUrl,
        DATABASE_URL_E2E: e2eDatabaseUrl,
        USE_MOCK_FALLBACK: 'true',
        MARKET_DATA_TOKEN: isLiveSmoke ? (process.env.MARKET_DATA_TOKEN || '') : '',
        PORT: '5010',
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: '/Users/samuel/Documents/stock_pattern_project/frontend',
      url: 'http://127.0.0.1:4173/',
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
