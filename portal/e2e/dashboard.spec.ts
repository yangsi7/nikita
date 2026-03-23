import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectCardContent, expectDataLoaded } from "./fixtures/assertions"
import { collectConsoleErrors, assertNoConsoleErrors } from "./helpers"

/**
 * Player dashboard E2E tests — deterministic rendering with mocked API data.
 * Uses mockApiRoutes for deterministic data, content assertions for real validation.
 */

test.describe("Dashboard — Score Ring & Hero Section", () => {
  test("dashboard renders relationship hero with score and chapter", async ({ page }) => {
    const errors = collectConsoleErrors(page)
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Score ring shows the mocked score (62)
    await expectCardContent(page, "card-score-ring", "62")
    // Chapter name from mock
    await expectCardContent(page, "card-score-ring", "Infatuation")
    // Game status badge
    await expectCardContent(page, "card-score-ring", "active")

    assertNoConsoleErrors(errors)
  })

  test("dashboard shows days played count", async ({ page }) => {
    const errors = collectConsoleErrors(page)
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    await expectCardContent(page, "card-score-ring", "12 days played")

    assertNoConsoleErrors(errors)
  })
})

test.describe("Dashboard — Score Timeline Chart", () => {
  test("dashboard renders score timeline SVG chart", async ({ page }) => {
    const errors = collectConsoleErrors(page)
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // The page should contain at least one SVG (score timeline chart)
    const svgCount = await page.locator("svg").count()
    expect(svgCount, "Dashboard should render at least one chart SVG").toBeGreaterThan(0)

    assertNoConsoleErrors(errors)
  })
})

test.describe("Dashboard — Navigation Between Player Pages", () => {
  const playerPages = [
    { name: "Engagement", path: "/dashboard/engagement" },
    { name: "Vices", path: "/dashboard/vices" },
    { name: "Conversations", path: "/dashboard/conversations" },
  ]

  for (const pg of playerPages) {
    test(`sidebar navigation to ${pg.name} works`, async ({ page }) => {
      const errors = collectConsoleErrors(page)
      await mockApiRoutes(page)
      await page.goto("/dashboard", { waitUntil: "networkidle" })
      await expectDataLoaded(page)

      const link = page.locator(`a[href="${pg.path}"]`).first()
      await expect(link).toBeVisible({ timeout: 5_000 })
      await link.click()
      await page.waitForURL(`**${pg.path}`)
      expect(page.url()).toContain(pg.path)

      assertNoConsoleErrors(errors)
    })
  }
})

test.describe("Dashboard — Loading Skeletons", () => {
  test("dashboard shows skeleton loading states while API is delayed", async ({ page }) => {
    // Mock API to delay response so skeletons remain visible
    await page.route("**/api/v1/**", async (route) => {
      await new Promise((r) => setTimeout(r, 5_000))
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      })
    })

    await page.goto("/dashboard", { waitUntil: "domcontentloaded" })

    // Check for skeleton loading indicators
    const skeletonCount = await page.locator("[data-testid^='skeleton-']").count()
    expect(skeletonCount, "Skeletons should be visible while API is delayed").toBeGreaterThan(0)
  })
})
