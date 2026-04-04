import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded, expectCardContent } from "./fixtures/assertions"

/**
 * Nikita's World E2E tests — hub page + 4 sub-pages with deterministic mock data.
 */

test.describe("Nikita Hub — /dashboard/nikita", () => {
  test("hub page renders MoodOrb and content sections", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Page heading
    await expect(page.locator("h1", { hasText: "Nikita's World" })).toBeVisible({ timeout: 5_000 })

    // MoodOrb card (data-testid="card-mood-orb")
    await expectCardContent(page, "card-mood-orb", /warm|content/i)

    // "Today's Events" section
    await expect(page.getByText("Today's Events")).toBeVisible()

    // "What's on Her Mind" section
    await expect(page.getByText("What's on Her Mind")).toBeVisible()
  })

  test("hub page has nav cards to sub-pages", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Storylines nav card links to /dashboard/nikita/stories
    const storiesLink = page.locator('a[href="/dashboard/nikita/stories"]')
    await expect(storiesLink).toBeVisible()
    await expect(storiesLink).toContainText("Storylines")

    // Social Circle nav card links to /dashboard/nikita/circle
    const circleLink = page.locator('a[href="/dashboard/nikita/circle"]')
    await expect(circleLink).toBeVisible()
    await expect(circleLink).toContainText("Social Circle")
  })

  test("Today's Events shows mock life events", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock life events include "team stand-up" and "Met Anya for coffee"
    const main = page.locator("main")
    await expect(main).toContainText(/stand-up|Anya/i)
  })

  test("What's on Her Mind shows mock thoughts", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock thoughts: "I wonder what they did today..."
    const main = page.locator("main")
    await expect(main).toContainText("wonder what they did")
  })
})

test.describe("Nikita Day — /dashboard/nikita/day", () => {
  test("day page renders with date navigation", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/day", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Heading
    await expect(page.locator("h1", { hasText: "Nikita's Day" })).toBeVisible()

    // Date nav buttons (Previous day / Next day)
    await expect(page.getByRole("button", { name: "Previous day" })).toBeVisible()
    await expect(page.getByRole("button", { name: "Next day" })).toBeVisible()
  })

  test("day page shows mock events", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/day", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock life events: "team stand-up", "Met Anya for coffee"
    const main = page.locator("main")
    await expect(main).toContainText(/stand-up|Anya/i)
  })

  test("previous day button navigates to prior date", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/day", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Get initial date text
    const dateLabel = page.locator("span.text-sm.text-muted-foreground").first()
    const initialText = await dateLabel.textContent()

    // Click previous day
    await page.getByRole("button", { name: "Previous day" }).click()
    await page.waitForTimeout(500)

    // Date text should change
    const newText = await dateLabel.textContent()
    expect(newText, "Date label should change after clicking Previous day").not.toBe(initialText)
  })
})

test.describe("Nikita Mind — /dashboard/nikita/mind", () => {
  test("mind page renders thoughts", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/mind", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Heading
    await expect(page.locator("h1", { hasText: "Nikita's Mind" })).toBeVisible()

    // Mock thought: "I wonder what they did today..."
    const main = page.locator("main")
    await expect(main).toContainText("wonder what they did")
  })

  test("mind page shows thought count", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/mind", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Mock has 1 thought → "1 thought" label
    await expect(page.getByText("1 thought")).toBeVisible()
  })
})

test.describe("Nikita Stories — /dashboard/nikita/stories", () => {
  test("stories page renders active arcs", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/stories", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Heading
    await expect(page.locator("h1", { hasText: "Storylines" })).toBeVisible()

    // Active arcs section
    await expect(page.getByText("Active Arcs")).toBeVisible()

    // Mock arc: "Weekend Getaway"
    await expect(page.locator("main")).toContainText("Weekend Getaway")
  })

  test("Show resolved toggle reveals resolved arcs", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/stories", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // "Resolved Arcs" section should NOT be visible initially
    await expect(page.getByText("Resolved Arcs")).not.toBeVisible()

    // Click "Show resolved"
    await page.getByRole("button", { name: "Show resolved" }).click()

    // "Resolved Arcs" section should now be visible with mock data
    await expect(page.getByText("Resolved Arcs")).toBeVisible({ timeout: 3_000 })
    await expect(page.locator("main")).toContainText("First Fight")

    // Toggle back — "Hide resolved"
    await page.getByRole("button", { name: "Hide resolved" }).click()
    await expect(page.getByText("Resolved Arcs")).not.toBeVisible()
  })
})

test.describe("Nikita Circle — /dashboard/nikita/circle", () => {
  test("circle page renders friends gallery with count", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/dashboard/nikita/circle", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Heading
    await expect(page.locator("h1", { hasText: "Social Circle" })).toBeVisible()

    // Count header — mock has 2 friends
    await expect(page.getByText("2 friends")).toBeVisible()

    // Friend names from mock: "Anya" and "Marcus"
    const main = page.locator("main")
    await expect(main).toContainText("Anya")
    await expect(main).toContainText("Marcus")
  })
})
