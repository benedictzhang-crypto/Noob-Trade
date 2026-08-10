import { expect, test } from '@playwright/test'

test.describe('More page', () => {
  test('shows the NoobTrade product story and feedback channels', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    await page.getByRole('button', { name: 'More' }).click()

    await expect(page.getByText('What NoobTrade is building')).toBeVisible()
    await expect(page.getByText('About NoobTrade')).toBeVisible()
    await expect(page.getByText('What the platform helps with')).toBeVisible()
    await expect(page.getByText('Write to the team')).toBeVisible()
    await expect(page.getByRole('link', { name: 'benedictzhang01@gmail.com' })).toHaveCount(2)
    await expect(page.getByRole('link', { name: '@NoobTrade123 on X' })).toBeVisible()
  })
})
