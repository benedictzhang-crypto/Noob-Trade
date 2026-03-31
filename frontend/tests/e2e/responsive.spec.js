import { expect, test } from '@playwright/test'

function pageFitsViewport() {
  return document.documentElement.scrollWidth <= window.innerWidth + 1
}

test.describe('Responsive layout smoke', () => {
  test('keeps Home and Markets usable on a mobile viewport', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('Noob Trade', { exact: true })).toBeVisible()
    await expect(page.getByText('Learn the tape before you risk real money.')).toBeVisible()
    await expect.poll(() => page.evaluate(pageFitsViewport)).toBe(true)

    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    await page.getByRole('button', { name: 'Markets' }).click()
    await expect(page.getByText('Signal, news, and social pulse')).toBeVisible()
    await expect.poll(() => page.evaluate(pageFitsViewport)).toBe(true)
  })
})
