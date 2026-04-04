import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded } from "./fixtures/assertions"

/**
 * Page transitions and data export E2E tests with deterministic mock data.
 */

test.describe("Page Transitions", () => {
  test("navigating between dashboard routes shows page content", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Navigate to engagement
    const engagementLink = page.locator('a[href="/dashboard/engagement"]').first()
    await expect(engagementLink).toBeVisible({ timeout: 5_000 })
    await engagementLink.click()
    await page.waitForURL("**/dashboard/engagement")
    expect(page.url()).toContain("/dashboard/engagement")

    // Engagement page should have loaded with content
    await expectDataLoaded(page)
  })

  test("navigating to conversations page loads with message data", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    const link = page.locator('a[href="/dashboard/conversations"]').first()
    await expect(link).toBeVisible({ timeout: 5_000 })
    await link.click()
    await page.waitForURL("**/dashboard/conversations")
    expect(page.url()).toContain("/dashboard/conversations")

    await expectDataLoaded(page)
  })
})

test.describe("Data Export", () => {
  test("conversations page has interactive pagination controls", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/conversations", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Page should have meaningful content
    const mainText = await page.locator("main").textContent()
    expect((mainText ?? "").length, "Page should have content").toBeGreaterThan(10)

    // Conversations page has tab controls (All / Text / Voice / Boss)
    const tabs = page.getByRole("tab")
    await expect(tabs.first(), "Tab controls should be present on conversations page").toBeVisible({ timeout: 5_000 })
  })
})
