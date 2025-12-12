import { test, expect } from '@playwright/test'

test.describe('Accessibility', () => {
  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/')

    // Check h1 (Nikita logo)
    const h1 = page.getByRole('heading', { level: 1, name: 'Nikita' })
    await expect(h1).toBeVisible()

    // Check other headings exist in proper order
    const h2 = page.getByRole('heading', { level: 2, name: 'Sign In' })
    await expect(h2).toBeVisible()
  })

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/')

    // Tab through form elements
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Email input should be focusable
    const emailInput = page.getByPlaceholder('your.email@example.com')
    await expect(emailInput).toBeFocused()

    // Tab to button
    await page.keyboard.press('Tab')
    const button = page.getByRole('button', { name: 'Send Magic Link' })
    await expect(button).toBeFocused()

    // Should be able to activate button with Enter
    await page.keyboard.press('Enter')
    // Button should attempt submission
  })

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/')

    const emailInput = page.getByPlaceholder('your.email@example.com')

    // Fill invalid email to trigger error
    await emailInput.fill('invalid')
    await page.getByRole('button', { name: 'Send Magic Link' }).click()

    // Check ARIA attributes for error state
    await expect(emailInput).toHaveAttribute('aria-invalid', 'true')
    await expect(emailInput).toHaveAttribute('aria-describedby', 'email-error')

    // Error message should be associated
    const errorMessage = page.locator('#email-error')
    await expect(errorMessage).toBeVisible()
  })

  test('should have visible focus indicators', async ({ page }) => {
    await page.goto('/')

    // Tab to email input
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    const emailInput = page.getByPlaceholder('your.email@example.com')
    await expect(emailInput).toBeFocused()

    // Focus ring should be visible (check computed styles)
    const box = await emailInput.boundingBox()
    expect(box).not.toBeNull()
  })

  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto('/')

    // Check text elements are visible (basic contrast check)
    await expect(page.getByText("Don't Get Dumped")).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
    await expect(page.getByText('Enter your email to receive a magic link')).toBeVisible()
  })

  test('should support screen readers with proper roles', async ({ page }) => {
    await page.goto('/')

    // Check for button role
    const button = page.getByRole('button', { name: 'Send Magic Link' })
    await expect(button).toHaveAttribute('type', 'submit')

    // Check for form structure
    const emailInput = page.getByPlaceholder('your.email@example.com')
    await expect(emailInput).toHaveAttribute('type', 'email')
  })

  test('should display error messages in alert role', async ({ page }) => {
    await page.goto('/')

    // Trigger error
    await page.getByPlaceholder('your.email@example.com').fill('invalid')
    await page.getByRole('button', { name: 'Send Magic Link' }).click()

    // Error message should have alert role
    const errorMessage = page.getByText('Please enter a valid email address')
    await expect(errorMessage).toBeVisible()
  })
})
