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

    await expect(page.getByText('NoobTrade', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Home' })).toBeVisible()

    await signInAndOpenAnalysis(page)

    const searchInput = page.getByPlaceholder('Enter Ticker (e.g. AAPL)')
    const aaplResponse = await request.get('http://127.0.0.1:5010/api/stock/AAPL?lookback=20&interval=daily&indicators=MA,EMA,MACD,BOLL,Vol&persist=1&usage=warmup')
    expect(aaplResponse.ok()).toBeTruthy()
    const aaplData = await aaplResponse.json()
    await page.evaluate((responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData), aaplData)

    await expect(page.getByText('Prediction Summary')).toBeVisible()
    await expect(searchInput).toHaveValue('AAPL')
    await expect(page.getByText('Data Source')).toBeVisible()
    await expect(page.locator('.source-pill').first()).toContainText(/Market Data|Mock Data|Live API/)
    await expect(page.getByText('Target Price')).toBeVisible()
    await expect(page.getByText('Matched Historical Patterns')).toBeVisible()

    await page.locator('.match-row--interactive').first().click()
    const replayModal = page.locator('.replay-modal')
    const replayChart = replayModal.locator('.chart-main-shell')
    await expect(replayModal).toBeVisible()
    await expect(replayChart).toBeVisible()

    const replayScrollStyles = await replayModal.evaluate((element) => {
      const styles = window.getComputedStyle(element)
      return {
        overflowY: styles.overflowY,
        touchAction: styles.touchAction,
      }
    })
    expect(replayScrollStyles.overflowY).toBe('auto')
    expect(replayScrollStyles.touchAction).toContain('pan-y')

    const ordinaryWheelPrevented = await replayChart.evaluate((element) => {
      const event = new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: 120 })
      return !element.dispatchEvent(event)
    })
    const zoomWheelPrevented = await replayChart.evaluate((element) => {
      const event = new WheelEvent('wheel', { bubbles: true, cancelable: true, ctrlKey: true, deltaY: -120 })
      return !element.dispatchEvent(event)
    })
    expect(ordinaryWheelPrevented).toBeFalsy()
    expect(zoomWheelPrevented).toBeTruthy()
    await replayModal.getByRole('button', { name: 'Close' }).click()

    await setInterval(page, 'weekly')
    await expect(page.getByText('Weekly Candles')).toBeVisible()

    await setInterval(page, 'monthly')
    await expect(page.getByText('Monthly Candles')).toBeVisible()

    await setInterval(page, 'daily')
    await expect(page.getByText('Daily Candles')).toBeVisible()

    const indicatorList = page.locator('.indicator-list')
    const rsiButton = indicatorList.getByRole('button', { name: /RSI/i })
    await expect(rsiButton).toHaveClass(/active/)
    await rsiButton.click()
    await expect(rsiButton).not.toHaveClass(/active/)
    await rsiButton.click()
    await expect(rsiButton).toHaveClass(/active/)

    const tslaResponse = await request.get('http://127.0.0.1:5010/api/stock/TSLA?lookback=20&interval=daily&indicators=MA,EMA,MACD,BOLL,RSI,Vol&persist=1&usage=warmup')
    expect(tslaResponse.ok()).toBeTruthy()
    const tslaData = await tslaResponse.json()
    await page.evaluate((responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData), tslaData)

    await expect(searchInput).toHaveValue('TSLA')
    await expect(page.getByText('TSLA Forecast')).toBeVisible()

    const counts = await getCoreTableCounts()
    expect(counts.symbols).toBeGreaterThanOrEqual(2)
    expect(counts.daily_prices).toBeGreaterThan(0)
    expect(counts.daily_indicators).toBeGreaterThan(0)
    expect(counts.pattern_windows).toBeGreaterThan(0)
    expect(counts.analysis_runs).toBeGreaterThanOrEqual(2)
    expect(counts.pattern_matches).toBeGreaterThan(0)
  })

  test('shows a loading state while waiting for stock data', async ({ page }) => {
    await page.route('**/api/stock/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 700))
      await route.continue()
    })

    await page.goto('/')
    await signInAndOpenAnalysis(page)

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

    await runSearch(page, 'AAPL-1')
    await expect(page.getByText('Please enter a valid symbol, such as AAPL or BRK.B.')).toBeVisible()
  })

  test('calibrates only complete indicator selections in the rendered summary', async ({ page }) => {
    await page.goto('/')
    await signInAndOpenAnalysis(page)

    const buildResponse = (indicators, probability) => ({
      dataSource: 'live',
      request: { symbol: 'AAPL', interval: 'daily', indicators },
      stock: { symbol: 'AAPL', companyName: 'Apple', currentPrice: 200 },
      patternAnalysis: {
        probabilityOfIncrease: probability,
        probabilityOfDecrease: 40,
        matchedPatternsCount: 20,
        matchedHistoricalPatterns: [],
        highFitHistoricalPaths: [],
        probabilityCalibrationSummary: {
          method: 'similarity_weighted_v2',
          sampleSize: 20,
          top1Similarity: 70,
          top10AverageSimilarity: 50,
        },
        futureFiveDayProbabilities: {
          up: [{ threshold: 1, probability }],
          down: [{ threshold: 1, probability: 40 }],
        },
      },
      chartData: { series: { daily: [] } },
    })
    const fullIndicators = ['MA', 'EMA', 'MACD', 'BOLL', 'RSI', 'Vol', 'KDJ', 'OI', 'OBV']

    await page.evaluate((responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData), buildResponse(fullIndicators, 100))
    await expect(page.locator('.summary-hero h3')).toHaveText('93.9%')

    await page.evaluate(
      (responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData),
      buildResponse(fullIndicators.filter((name) => name !== 'OI'), 87.35),
    )
    await expect(page.locator('.summary-hero h3')).toHaveText('87%')
  })

  test('shows a friendly error when the backend request fails', async ({ page }) => {
    await page.route('**/api/stock/**', async (route) => {
      await route.abort()
    })

    await page.goto('/')
    await signInAndOpenAnalysis(page)

    await runSearch(page, 'XYZTEST', { lookback: 20 })

    await expect(page.locator('.error-message')).toContainText(/Failed to fetch|not accessible|timed out/i)
  })
})
