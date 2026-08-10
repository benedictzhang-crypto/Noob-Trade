import { expect, test } from '@playwright/test'

test.describe('Required page structure', () => {
  test('covers public entry pages and the authenticated dashboard flow', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('button', { name: 'Home' })).toBeVisible()
    await expect(page.getByText('Learn the tape before you risk real money.')).toBeVisible()

    await page.getByRole('navigation').getByRole('button', { name: 'Register' }).click()
    await expect(page.getByText('Register for NoobTrade')).toBeVisible()

    await page.getByRole('navigation').getByRole('button', { name: 'Sign In', exact: true }).click()
    await expect(page.getByText('Sign in to your workspace')).toBeVisible()

    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    await expect(page.getByRole('heading', { name: 'Stock probability scan center.' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Dashboard' })).toBeVisible()
  })

  test('includes the current authenticated navigation pages', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())

    await page.getByRole('button', { name: 'Stock Trade' }).click()
    await expect(page.getByRole('heading', { name: 'Stock Trade Desk' })).toBeVisible()

    await page.getByRole('button', { name: 'Explore' }).click()
    await expect(page.getByRole('heading', { name: 'Ranked market board for scanning all stocks.' })).toBeVisible()

    await page.getByRole('button', { name: 'Settings' }).click()
    await expect(page.getByRole('heading', { name: 'Your account at a glance' })).toBeVisible()

    await page.getByRole('button', { name: 'More' }).click()
    await expect(page.getByRole('heading', { name: 'What NoobTrade is building' })).toBeVisible()
  })
})
