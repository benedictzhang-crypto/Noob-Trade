import { expect, test } from '@playwright/test'

import { getCoreTableCounts, resetDatabase } from './helpers/db.js'

async function signInAndOpenAnalysis(page) {
  await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
  await page.evaluate(() => window.__NOOB_TRADE_E2E__.setPage('Analysis'))
}

async function runSearch(page, symbol, options = {}) {
  return page.evaluate(
    ({ nextSymbol, nextOptions }) => window.__NOOB_TRADE_E2E__.search(nextSymbol, nextOptions),
    { nextSymbol: symbol, nextOptions: options }
  )
}

async function setInterval(page, interval) {
  return page.evaluate((nextInterval) => window.__NOOB_TRADE_E2E__.setInterval(nextInterval), interval)
}

test.describe('Analysis workspace', () => {
  test.beforeEach(async () => {
    await resetDatabase()
  })

  test('runs the main analysis workflow and persists data end-to-end', async ({ page, request }) => {
    await page.goto('/')

    await expect(page.getByText('Noob Trade', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Home' })).toBeVisible()

    await signInAndOpenAnalysis(page)

    await page.locator('#lookback').selectOption('20')

    const searchInput = page.getByPlaceholder('Enter Ticker (e.g. AAPL)')
    const aaplResponse = await request.get('http://127.0.0.1:5010/api/stock/AAPL?lookback=20&interval=daily&indicators=MA,EMA,MACD,BOLL,Vol')
    expect(aaplResponse.ok()).toBeTruthy()
    const aaplData = await aaplResponse.json()
    await page.evaluate((responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData), aaplData)

    await expect(page.getByText('Prediction Summary')).toBeVisible()
    await expect(searchInput).toHaveValue('AAPL')
    await expect(page.getByText('Data Source')).toBeVisible()
    await expect(page.locator('.source-pill').first()).toContainText(/Mock Data|Live API/)
    await expect(page.getByText('Suggested Sell Price')).toBeVisible()
    await expect(page.getByText('Matched Historical Patterns')).toBeVisible()
    await expect(page.getByText('High-Fit Historical Paths')).toBeVisible()
    await expect(page.getByText('Paper Trading Panel')).toBeVisible()

    await setInterval(page, 'weekly')
    await expect(page.getByText('Weekly Candles')).toBeVisible()

    await setInterval(page, 'monthly')
    await expect(page.getByText('Monthly Candles')).toBeVisible()

    await setInterval(page, 'daily')
    await expect(page.getByText('Daily Candles')).toBeVisible()

    const indicatorList = page.locator('.indicator-list')
    await indicatorList.getByRole('button', { name: /RSI/i }).click()
    await expect(page.locator('.indicator-metric-card').filter({ hasText: 'RSI' })).toBeVisible()

    await indicatorList.getByRole('button', { name: /MACD/i }).click()
    await expect(page.getByText('Histogram, MACD, and Signal')).toHaveCount(0)
    await indicatorList.getByRole('button', { name: /MACD/i }).click()
    await expect(page.getByText('Histogram, MACD, and Signal')).toBeVisible()

    const tslaResponse = await request.get('http://127.0.0.1:5010/api/stock/TSLA?lookback=20&interval=daily&indicators=MA,EMA,MACD,BOLL,RSI,Vol')
    expect(tslaResponse.ok()).toBeTruthy()
    const tslaData = await tslaResponse.json()
    await page.evaluate((responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData), tslaData)

    await expect(searchInput).toHaveValue('TSLA')
    await expect(page.getByText('TSLA Forecast')).toBeVisible()

    const counts = await getCoreTableCounts()
    expect(counts.symbols).toBe(2)
    expect(counts.daily_prices).toBeGreaterThan(0)
    expect(counts.daily_indicators).toBeGreaterThan(0)
    expect(counts.pattern_windows).toBeGreaterThan(0)
    expect(counts.analysis_runs).toBe(2)
    expect(counts.pattern_matches).toBeGreaterThan(0)
  })

  test('shows a loading state while waiting for stock data', async ({ page }) => {
    await page.route('**/api/stock/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 700))
      await route.continue()
    })

    await page.goto('/')
    await signInAndOpenAnalysis(page)
    await page.locator('#lookback').selectOption('20')

    const searchInput = page.getByPlaceholder('Enter Ticker (e.g. AAPL)')
    const pendingSearch = runSearch(page, 'AAPL', { lookback: 20 })

    await expect(page.getByRole('button', { name: 'Loading...' })).toBeVisible()
    await expect(page.getByText('Loading stock data for AAPL...')).toBeVisible()
    await pendingSearch
    await expect(page.getByText('Prediction Summary')).toBeVisible()
  })

  test('shows validation errors for empty and invalid symbols', async ({ page }) => {
    await page.goto('/')
    await signInAndOpenAnalysis(page)

    const searchInput = page.getByPlaceholder('Enter Ticker (e.g. AAPL)')
    await searchInput.fill('')
    await runSearch(page, '')
    await expect(page.getByText('Please enter a stock symbol before searching.')).toBeVisible()

    await runSearch(page, 'AAPL1')
    await expect(page.getByText('Please enter a valid symbol using letters only, such as AAPL.')).toBeVisible()
  })

  test('shows a friendly error when the backend request fails', async ({ page }) => {
    await page.route('**/api/stock/**', async (route) => {
      await route.abort()
    })

    await page.goto('/')
    await signInAndOpenAnalysis(page)
    await page.locator('#lookback').selectOption('20')

    const searchInput = page.getByPlaceholder('Enter Ticker (e.g. AAPL)')
    await runSearch(page, 'AAPL', { lookback: 20 })

    await expect(
      page.getByText('We could not load stock data. Please make sure the Flask backend is running and try again.')
    ).toBeVisible()
  })
})
