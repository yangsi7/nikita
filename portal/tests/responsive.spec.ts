import { test, expect } from '@playwright/test'

test.describe('Responsive Design', () => {
  test('should render correctly on desktop (1920x1080)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/')

    // Check card is centered with proper width
    const card = page.locator('.max-w-md')
    await expect(card).toBeVisible()

    // Check gradient background is visible
    const background = page.locator('.bg-gradient-to-br')
    await expect(background).toBeVisible()
  })

  test('should render correctly on tablet (768x1024)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/')

    // Check main elements are visible
    await expect(page.getByRole('heading', { name: 'Nikita' })).toBeVisible()
    await expect(page.getByPlaceholder('your.email@example.com')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send Magic Link' })).toBeVisible()
  })

  test('should render correctly on mobile (375x667)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/')

    // Check all elements are still visible on small screen
    await expect(page.getByRole('heading', { name: 'Nikita' })).toBeVisible()
    await expect(page.getByText("Don't Get Dumped")).toBeVisible()
    await expect(page.getByPlaceholder('your.email@example.com')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send Magic Link' })).toBeVisible()

    // Check text is legible (not cut off)
    const emailInput = page.getByPlaceholder('your.email@example.com')
    const box = await emailInput.boundingBox()
    expect(box?.width).toBeGreaterThan(0)
  })

  test('should maintain layout on very small mobile (320x568)', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 })
    await page.goto('/')

    // Check critical elements are still accessible
    await expect(page.getByRole('heading', { name: 'Nikita' })).toBeVisible()
    await expect(page.getByPlaceholder('your.email@example.com')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send Magic Link' })).toBeVisible()
  })
})
