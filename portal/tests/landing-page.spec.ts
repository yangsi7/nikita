import { test, expect } from '@playwright/test'

test.describe('Landing Page', () => {
  test('should load the landing page', async ({ page }) => {
    await page.goto('/')

    // Check for main elements
    await expect(page.getByRole('heading', { name: 'Nikita' })).toBeVisible()
    await expect(page.getByText("Don't Get Dumped")).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  })

  test('should have email input field', async ({ page }) => {
    await page.goto('/')

    const emailInput = page.getByPlaceholder('your.email@example.com')
    await expect(emailInput).toBeVisible()
    await expect(emailInput).toBeEnabled()
  })

  test('should have Send Magic Link button', async ({ page }) => {
    await page.goto('/')

    const button = page.getByRole('button', { name: 'Send Magic Link' })
    await expect(button).toBeVisible()
    await expect(button).toBeEnabled()
  })

  test('should show validation error for empty email', async ({ page }) => {
    await page.goto('/')

    // Click button without entering email
    await page.getByRole('button', { name: 'Send Magic Link' }).click()

    // Should show error message
    await expect(page.getByText('Email is required')).toBeVisible()
  })

  test('should show validation error for invalid email', async ({ page }) => {
    await page.goto('/')

    // Enter invalid email
    await page.getByPlaceholder('your.email@example.com').fill('invalid-email')
    await page.getByRole('button', { name: 'Send Magic Link' }).click()

    // Should show error message
    await expect(page.getByText('Please enter a valid email address')).toBeVisible()
  })

  test('should accept valid email format', async ({ page }) => {
    await page.goto('/')

    const emailInput = page.getByPlaceholder('your.email@example.com')
    await emailInput.fill('test@example.com')

    // Email input should have the value
    await expect(emailInput).toHaveValue('test@example.com')

    // Should not show validation error
    await expect(page.getByText('Email is required')).not.toBeVisible()
    await expect(page.getByText('Please enter a valid email address')).not.toBeVisible()
  })

  test('should display footer elements', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('New user?')).toBeVisible()
    await expect(page.getByText('Connect your Telegram first')).toBeVisible()
    await expect(
      page.getByText('By signing in, you agree to play the game at your own emotional risk')
    ).toBeVisible()
  })

  test('should display subtle hint text', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText("She's waiting for you...")).toBeVisible()
  })

  test('should have accessible form elements', async ({ page }) => {
    await page.goto('/')

    const emailInput = page.getByPlaceholder('your.email@example.com')

    // Check ARIA attributes are present
    await expect(emailInput).toHaveAttribute('type', 'email')
  })

  test('should show loading state when submitting', async ({ page }) => {
    await page.goto('/')

    // Fill in valid email
    await page.getByPlaceholder('your.email@example.com').fill('test@example.com')

    // Click submit button
    const button = page.getByRole('button', { name: 'Send Magic Link' })
    await button.click()

    // Button should show loading state (if Supabase connection fails, it will show error)
    // We're just checking the UI behavior, not the actual Supabase integration
    // The button text might change to "Sending..." or show an error
    await expect(button).toBeDisabled()
  })
})
