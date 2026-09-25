import { expect, test } from '@playwright/test'

function pageFitsViewport() {
  return document.documentElement.scrollWidth <= window.innerWidth + 1
}

test.describe('Responsive layout smoke', () => {
  test('keeps Home and Markets usable on a mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')

    await expect(page.getByRole('img', { name: 'NoobTrade' })).toBeVisible()
    await expect(page.getByText('Learn the tape before you risk real money.')).toBeVisible()
    await expect.poll(() => page.evaluate(pageFitsViewport)).toBe(true)

    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    const mobileNavigation = page.getByRole('navigation', { name: 'Mobile navigation' })
    await expect(mobileNavigation.getByRole('button')).toHaveCount(5)
    await expect(mobileNavigation.getByRole('button', { name: 'Markets' })).toBeVisible()
    await expect(mobileNavigation.getByRole('button', { name: 'Settings' })).toBeVisible()
    await page.getByRole('button', { name: 'Markets' }).click()
    await expect(page.getByText('Signal, news, and social pulse')).toBeVisible()
    await expect.poll(() => page.evaluate(pageFitsViewport)).toBe(true)

    await mobileNavigation.getByRole('button', { name: 'Settings' }).click()
    await expect(page.getByRole('region', { name: 'Noob AI settings' })).toBeVisible()
    await expect(page.locator('.voice-assistant')).toBeHidden()
    await expect.poll(() => page.evaluate(pageFitsViewport)).toBe(true)
  })

  test('uses a paged mobile trade workflow with a three-column indicator grid', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    await page.evaluate(() => {
      window.__NOOB_TRADE_E2E__.signIn()
      window.__NOOB_TRADE_E2E__.setPage('Stock Trade')
    })

    await expect(page.getByRole('heading', { name: 'Stock Trade Desk' })).toBeVisible()
    await expect(page.getByText('Select Indicators')).toBeHidden()
    await expect(page.locator('.topbar-actions')).toBeHidden()

    const indicators = ['MA', 'EMA', 'MACD', 'BOLL', 'RSI', 'Vol', 'KDJ', 'OI', 'OBV']
    await page.evaluate((selectedIndicators) => window.__NOOB_TRADE_E2E__.applyResponse({
      dataSource: 'live',
      request: { symbol: 'AAPL', interval: 'daily', indicators: selectedIndicators },
      stock: { symbol: 'AAPL', companyName: 'Apple Inc.', currentPrice: 205.4 },
      patternAnalysis: {
        selectedIndicators,
        probabilityOfIncrease: 72.4,
        probabilityOfDecrease: 38.1,
        matchedPatternsCount: 20,
        matchedHistoricalPatterns: [],
        highFitHistoricalPaths: [],
        futureFiveDayProbabilities: {
          up: [{ threshold: 1, probability: 72.4 }],
          down: [{ threshold: 1, probability: 38.1 }],
        },
      },
      chartData: { series: { daily: [] } },
    }), indicators)

    await page.getByRole('button', { name: /Indicators/ }).first().click()
    const indicatorGrid = page.locator('.indicator-list')
    const mobileActions = page.getByRole('region', { name: 'Trade step actions' })
    const mobileNavigation = page.getByRole('navigation', { name: 'Mobile navigation' })
    await expect(indicatorGrid.getByRole('button')).toHaveCount(9)
    await expect(mobileActions).toBeVisible()
    await expect(page.locator('.voice-assistant')).toBeHidden()
    await expect.poll(() => indicatorGrid.evaluate((element) => (
      window.getComputedStyle(element).gridTemplateColumns.split(' ').filter(Boolean).length === 3
    ))).toBe(true)
    await expect.poll(async () => {
      const [actionsBox, navigationBox] = await Promise.all([
        mobileActions.boundingBox(),
        mobileNavigation.boundingBox(),
      ])
      return Boolean(actionsBox && navigationBox && actionsBox.y + actionsBox.height <= navigationBox.y)
    }).toBe(true)

    await page.getByRole('button', { name: /Results/ }).first().click()
    await expect(page.getByRole('tablist', { name: 'Result view' })).toBeVisible()
    await expect(page.getByText('Prediction Summary')).toBeVisible()
    await page.getByRole('button', { name: 'History' }).click()
    await expect(page.getByText('Matched Historical Patterns')).toBeVisible()
    await expect.poll(() => page.evaluate(pageFitsViewport)).toBe(true)
  })
})
