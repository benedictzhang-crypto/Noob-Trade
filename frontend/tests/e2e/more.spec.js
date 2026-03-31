import { expect, test } from '@playwright/test'

test.describe('More page', () => {
  test('shows the Noob Trade product story and feedback channels', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    await page.getByRole('button', { name: 'More' }).click()

    await expect(page.getByText('What Noob Trade is building')).toBeVisible()
    await expect(page.getByText('About Noob Trade')).toBeVisible()
    await expect(page.getByText('What the platform helps with')).toBeVisible()
    await expect(page.getByText('Write to the team')).toBeVisible()
    await expect(page.getByText('feedback@noobtrade.app')).toBeVisible()
    await expect(page.getByText('research@noobtrade.app')).toBeVisible()
    await expect(page.getByText('@NoobTradeDesk on X')).toBeVisible()
  })
})
