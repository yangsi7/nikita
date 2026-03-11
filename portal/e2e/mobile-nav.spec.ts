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
  test("mobile nav has correct route hrefs", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Verify nav links point to correct routes (actual route rendering
    // is covered by player.spec.ts smoke tests for each route)
    const nav = page.locator('[data-testid="nav-mobile"]')
    await expect(nav.locator('a[href="/dashboard"]')).toBeVisible()
    await expect(nav.locator('a[href="/dashboard/engagement"]')).toBeVisible()
    await expect(nav.locator('a[href="/dashboard/nikita"]')).toBeVisible()
    await expect(nav.locator('a[href="/dashboard/vices"]')).toBeVisible()
    await expect(nav.locator('a[href="/dashboard/conversations"]')).toBeVisible()
  })
})
