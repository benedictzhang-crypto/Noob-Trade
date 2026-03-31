import { expect, test } from '@playwright/test'

test.describe('Required page structure', () => {
  test('covers public entry pages and the authenticated dashboard flow', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('button', { name: 'Home' })).toBeVisible()
    await expect(page.getByText('Learn the tape before you risk real money.')).toBeVisible()

    await page.getByRole('button', { name: 'Register' }).click()
    await expect(page.getByText('Create your Noob Trade account')).toBeVisible()

    await page.getByRole('navigation').getByRole('button', { name: 'Sign In', exact: true }).click()
    await expect(page.getByText('Sign in to your workspace')).toBeVisible()

    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())
    await expect(page.getByText('Welcome back, Samuel Trader')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Dashboard' })).toBeVisible()
  })

  test('includes portfolio, history, and reports pages for authenticated users', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => window.__NOOB_TRADE_E2E__.signIn())

    await page.getByRole('button', { name: 'Portfolio' }).click()
    await expect(page.getByText('Portfolio analysis for current holdings')).toBeVisible()

    await page.getByRole('button', { name: 'History' }).click()
    await expect(page.getByText('History of executed trade decisions')).toBeVisible()

    await page.getByRole('navigation').getByRole('button', { name: 'Reports', exact: true }).click()
    await expect(page.getByText('Class-ready reporting functionality')).toBeVisible()
  })
})
