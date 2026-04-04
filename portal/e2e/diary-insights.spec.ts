import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded } from "./fixtures/assertions"

/**
 * Diary and Insights E2E tests with deterministic mock data.
 */

test.describe("Diary — /dashboard/diary", () => {
  test("diary page renders entry cards with date and content", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/diary", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Page heading
    await expect(page.locator("h2", { hasText: "Nikita's Diary" })).toBeVisible({ timeout: 5_000 })

    // Mock diary has 2 entries with data-testid="card-diary-{id}"
    const entry1 = page.locator('[data-testid="card-diary-diary-1"]')
    await expect(entry1, "First diary entry card should be visible").toBeVisible()

    const entry2 = page.locator('[data-testid="card-diary-diary-2"]')
    await expect(entry2, "Second diary entry card should be visible").toBeVisible()
  })

  test("diary entries show summary text from mock data", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/diary", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock diary-1 summary: "A warm day full of playful exchanges."
    const main = page.locator("main")
    await expect(main).toContainText("warm day full of playful exchanges")

    // Mock diary-2 summary: "Brief but meaningful connection."
    await expect(main).toContainText("Brief but meaningful connection")
  })

  test("diary entries display score deltas", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/diary", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock diary-1: score_start=60, score_end=63
    const main = page.locator("main")
    await expect(main).toContainText("60")
    await expect(main).toContainText("63")
  })
})

test.describe("Insights — /dashboard/insights", () => {
  test("insights page renders with heading", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/insights", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Page heading
    await expect(page.locator("h1", { hasText: "Deep Insights" })).toBeVisible({ timeout: 5_000 })
  })

  test("insights page renders ScoreDetailChart SVG", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/insights", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // ScoreDetailChart renders Recharts SVG
    const svgs = page.locator("svg")
    const svgCount = await svgs.count()
    expect(svgCount, "Insights page should render at least one SVG chart").toBeGreaterThan(0)
  })

  test("insights page shows Conversation Threads section", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/insights", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Thread section heading
    await expect(page.getByText("Conversation Threads")).toBeVisible()
  })
})
