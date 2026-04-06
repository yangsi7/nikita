import { test, expect } from "@playwright/test"

/**
 * Landing Page E2E tests — Spec 208
 *
 * Tests verify the public landing page at /:
 * - Always renders (no redirect) for all users
 * - Hero section content and CTA
 * - Pitch section and Telegram mockup
 * - System terminal section
 * - Stakes section and chapter timeline
 * - CTA section and footer
 * - Floating nav behavior
 * - SEO metadata
 */

test.describe("Landing Page — Spec 208", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 })
  })

  test("renders landing page (no redirect for unauthenticated users)", async ({ page }) => {
    // Should NOT redirect to /login
    const url = page.url()
    expect(url).not.toContain("/login")
    // Should render at root path
    expect(new URL(url).pathname).toBe("/")
  })

  test("renders H1 heading with Don't Get Dumped", async ({ page }) => {
    const h1 = page.getByRole("heading", { level: 1 })
    await expect(h1).toBeVisible({ timeout: 10_000 })
    await expect(h1).toContainText("Dumped")
  })

  test("renders eyebrow text with 18+", async ({ page }) => {
    await expect(page.getByText(/18\+/)).toBeVisible({ timeout: 10_000 })
  })

  test("renders subheadline — She remembers everything", async ({ page }) => {
    await expect(page.getByText(/She remembers everything/i)).toBeVisible({ timeout: 10_000 })
  })

  test("unauthenticated CTA links to Telegram", async ({ page }) => {
    // Find a visible link containing t.me — excludes nav CTA which is visibility:hidden until scroll
    const ctaLinks = page.locator("a[href*='t.me'], a[href*='telegram']")
    await expect(ctaLinks.filter({ visible: true }).first()).toBeVisible({ timeout: 10_000 })
  })

  test("renders pitch section with character caption", async ({ page }) => {
    // Scroll to pitch section
    await page.evaluate(() => window.scrollBy(0, window.innerHeight))
    await expect(page.getByText(/She has opinions/i)).toBeVisible({ timeout: 10_000 })
    // Extended Telegram conversation memory callback
    await expect(page.getByText(/i listen\. try it sometime/i)).toBeVisible({ timeout: 10_000 })
  })

  test("renders portal showcase section with 3 cards", async ({ page }) => {
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 2))
    await expect(page.getByRole("heading", { name: /a portal into her life/i })).toBeVisible({
      timeout: 10_000,
    })
    await expect(page.getByText(/her mood right now/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/your 30-day curve/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/what she's been up to/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test("renders stakes section with chapter timeline", async ({ page }) => {
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 4))
    await expect(page.getByText(/Spark/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/55%/)).toBeVisible({ timeout: 10_000 })
  })

  test("renders CTA section with copyright footer", async ({ page }) => {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await expect(page.getByText(/© 2026 Nanoleq/i)).toBeVisible({ timeout: 10_000 })
  })
})
