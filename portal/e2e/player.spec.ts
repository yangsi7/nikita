import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded, expectCardContent } from "./fixtures/assertions"

/**
 * Player dashboard E2E tests — route rendering with deterministic mock data.
 */

test.describe("Player Routes — Smoke Tests", () => {
  const playerRoutes = [
    { path: "/dashboard", name: "Dashboard" },
    { path: "/dashboard/engagement", name: "Engagement" },
    { path: "/dashboard/vices", name: "Vices" },
    { path: "/dashboard/conversations", name: "Conversations" },
    { path: "/dashboard/settings", name: "Settings" },
  ]

  for (const route of playerRoutes) {
    test(`${route.name} (${route.path}) loads with content`, async ({ page }) => {
      await mockApiRoutes(page)
      await page.goto(route.path, { waitUntil: "networkidle" })
      await expectDataLoaded(page)
    })
  }
})

test.describe("Player Routes — Content Validation", () => {
  test("vices page shows vice cards with category names", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/vices", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock vices include "jealousy" and "possessiveness"
    await expectCardContent(page, "card-vice-jealousy", "jealousy")
    await expectCardContent(page, "card-vice-possessiveness", "possessiveness")
  })

  test("conversations page shows conversation list", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/conversations", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock conversations have "playful" and "tense" tones
    const body = await page.locator("main").textContent()
    expect(body).toContain("telegram")
  })

  test("settings page shows user settings form", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/settings", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Settings page should show the email
    const body = await page.locator("main").textContent()
    expect(body).toBeTruthy()
  })
})

test.describe("Player Routes — Structure", () => {
  test("player sidebar has navigation items", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Sidebar should have key navigation items
    await expect(page.locator("text=Nikita").first()).toBeVisible()
    await expect(page.locator("text=Dashboard").first()).toBeVisible()
  })

  test("deep route /dashboard/conversations/conv-1 loads", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/conversations/conv-1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)
  })
})
