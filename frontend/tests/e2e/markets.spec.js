import { expect, test } from '@playwright/test'

import { resetDatabase } from './helpers/db.js'

test.describe('Markets page', () => {
  test.beforeEach(async () => {
    await resetDatabase()
  })

  test('shows symbol-aware news, trader posts, and spotlight context', async ({ page, request }) => {
    await page.goto('/')
    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    await page.evaluate(() => window.__NOOB_TRADE_E2E__.setPage('Analysis'))

    const tslaResponse = await request.get('http://127.0.0.1:5010/api/stock/TSLA?lookback=20&interval=daily&indicators=MA,EMA,MACD,BOLL,Vol&usage=warmup')
    expect(tslaResponse.ok()).toBeTruthy()
    const tslaData = await tslaResponse.json()
    await page.evaluate((responseData) => window.__NOOB_TRADE_E2E__.applyResponse(responseData), tslaData)
    await expect(page.getByText('TSLA Forecast')).toBeVisible()

    await page.getByRole('button', { name: 'Markets' }).click()

    await expect(page.getByRole('heading', { name: 'Hot Market News' })).toBeVisible()
    await expect(page.locator('.news-ticker-track')).toContainText('TSLA')
    await expect(page.getByText('X / Trader Posts')).toBeVisible()
    await expect(page.locator('.post-list')).toContainText('TSLA')
    await expect(page.getByText('Market Spotlight')).toBeVisible()
    await expect(page.locator('.spotlight-card')).toContainText('TSLA')
    await expect(page.getByText('Probability', { exact: true })).toBeVisible()
  })
})
