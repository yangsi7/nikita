import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded } from "./fixtures/assertions"

/**
 * Mobile navigation E2E tests — bottom nav bar visibility and routing.
 */

test.describe("Mobile Navigation — Visibility", () => {
  test("bottom nav visible at mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // MobileNav component should be visible at mobile width
    const mobileNav = page.locator('[data-testid="nav-mobile"]')
    await expect(mobileNav, "Mobile nav should be visible at 375px width").toBeVisible()
  })

  test("bottom nav hidden at desktop viewport", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 })
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // At desktop width, mobile nav should be hidden
    const mobileNav = page.locator('[data-testid="nav-mobile"]')
    await expect(mobileNav).toHaveCount(0)
  })
})

test.describe("Mobile Navigation — Route Changes", () => {
  test("mobile nav tabs navigate to correct routes", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Click the Engage tab (links to /dashboard/engagement)
    const engageLink = page.locator('[data-testid="nav-mobile"] a[href="/dashboard/engagement"]')
    await expect(engageLink).toBeVisible()
    await engageLink.click()
    await page.waitForURL("**/dashboard/engagement")
    expect(page.url()).toContain("/dashboard/engagement")
  })
})
