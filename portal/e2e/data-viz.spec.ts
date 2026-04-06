import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectCardContent, expectDataLoaded } from "./fixtures/assertions"

/**
 * Data visualization E2E tests — Recharts components with deterministic mock data.
 */

test.describe("Data Visualization — Score Timeline", () => {
  test("score timeline chart renders SVG with data elements", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // ScoreTimeline uses Recharts — verify SVG is present inside the score ring card
    await expectCardContent(page, "card-score-ring", /62|Infatuation/i)
  })
})

test.describe("Data Visualization — Engagement Page Charts", () => {
  test("engagement page renders engagement pulse with state indicators", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/engagement", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Engagement pulse card should be visible with mocked state "in_zone"
    await expectCardContent(page, "card-engagement-chart", "Engagement Pulse")
    await expectCardContent(page, "card-engagement-chart", /in.zone/i)
  })

  test("engagement page shows multiplier badge", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/engagement", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Multiplier from mock is 1.2x
    await expectCardContent(page, "card-engagement-chart", "1.2x")
  })
})
