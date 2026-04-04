import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded } from "./fixtures/assertions"

/**
 * Admin detail page E2E tests — /admin/users/[id] and /admin/conversations/[id].
 */

// Rich pipeline events for conversation inspector tests
function mockConversationEvents() {
  const now = new Date().toISOString()
  const events: PipelineEvent[] = [
    {
      id: "evt-1", user_id: "user-1", conversation_id: "conv-a1",
      event_type: "extraction.complete", stage: "extraction",
      data: { facts_count: 5, threads_count: 2, emotional_tone: "playful" },
      duration_ms: 120, created_at: now,
    },
    {
      id: "evt-2", user_id: "user-1", conversation_id: "conv-a1",
      event_type: "game_state.complete", stage: "game_state",
      data: { score_delta: 2.5, chapter: 2, chapter_changed: false },
      duration_ms: 45, created_at: now,
    },
    {
      id: "evt-3", user_id: "user-1", conversation_id: "conv-a1",
      event_type: "pipeline.complete", stage: "orchestrator",
      data: {
        success: true, total_duration_ms: 850,
        stages: [
          { name: "extraction", duration_ms: 120, status: "success" },
          { name: "game_state", duration_ms: 45, status: "success" },
          { name: "memory_write", duration_ms: 200, status: "success" },
        ],
      },
      duration_ms: 850, created_at: now,
    },
  ]
  return { conversation_id: "conv-a1", events, count: events.length }
}

test.describe("Admin User Detail — /admin/users/[id]", () => {
  test("user detail page renders breadcrumb and user info", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users/00000000-0000-0000-0000-000000000001", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Breadcrumb: Admin > Users > identifier
    await expect(page.locator("nav").getByText("Admin")).toBeVisible()
    await expect(page.locator("nav").getByText("Users")).toBeVisible()

    // User detail: mock user has phone="+1234567890", score=72, chapter=3
    const main = page.locator("main")
    await expect(main).toContainText("+1234567890")
    await expect(main).toContainText("72")
  })

  test("God Mode panel is visible with action buttons", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users/00000000-0000-0000-0000-000000000001", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // God Mode heading
    await expect(page.getByText("God Mode")).toBeVisible()

    // "Set Score" label and Set button
    await expect(page.getByText("Set Score (0-100)")).toBeVisible()
    const setButtons = page.getByRole("button", { name: "Set" })
    const setCount = await setButtons.count()
    expect(setCount, "Should have multiple Set buttons for score/chapter/status/engagement").toBeGreaterThanOrEqual(4)
  })

  test("Set Score button opens confirmation dialog, cancel closes it", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users/00000000-0000-0000-0000-000000000001", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Fill in a score value to enable the first Set button
    const scoreInput = page.locator('input[type="number"]').first()
    await scoreInput.fill("80")

    // Click the first enabled "Set" button (for Set Score)
    const setButtons = page.getByRole("button", { name: "Set" })
    await setButtons.first().click()

    // Confirmation dialog should appear
    await expect(page.getByText("Set Score")).toBeVisible({ timeout: 3_000 })
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible()
    await expect(page.getByRole("button", { name: "Confirm" })).toBeVisible()

    // Click Cancel — dialog should close
    await page.getByRole("button", { name: "Cancel" }).click()
    await expect(page.getByRole("button", { name: "Confirm" })).not.toBeVisible()
  })
})

test.describe("Admin Conversation Detail — /admin/conversations/[id]", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiRoutes(page)
    // Override the events endpoint to return rich mock data
    await page.route("**/api/v1/admin/conversations/conv-a1/events", (route) => {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockConversationEvents()),
      })
    })
  })

  test("conversation inspector renders title and breadcrumb", async ({ page }) => {
    await page.goto("/admin/conversations/conv-a1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Title
    await expect(page.locator("h1", { hasText: "Conversation Inspector" })).toBeVisible()

    // Breadcrumb
    await expect(page.locator("nav").getByText("Admin")).toBeVisible()
    await expect(page.locator("nav").getByText("Conversations")).toBeVisible()
  })

  test("conversation inspector shows SummaryCards with extracted data", async ({ page }) => {
    await page.goto("/admin/conversations/conv-a1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // SummaryCards: facts extracted=5, score delta=+2.5
    const main = page.locator("main")
    await expect(main).toContainText("5")
    await expect(main).toContainText("+2.5")
  })

  test("conversation inspector shows StageTimelineBar", async ({ page }) => {
    await page.goto("/admin/conversations/conv-a1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Stage durations label
    await expect(page.getByText("Stage durations (proportional)")).toBeVisible()

    // Stage names in legend: extraction, game_state, memory_write
    const main = page.locator("main")
    await expect(main).toContainText("extraction")
    await expect(main).toContainText("game_state")
    await expect(main).toContainText("memory_write")
  })

  test("conversation inspector has Event Timeline with clickable events", async ({ page }) => {
    await page.goto("/admin/conversations/conv-a1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Event Timeline heading
    await expect(page.getByText("Event Timeline")).toBeVisible()

    // At least 3 events rendered (extraction, game_state, pipeline)
    const eventButtons = page.locator(".glass-card button")
    const eventCount = await eventButtons.count()
    expect(eventCount, "Should have at least 3 events in timeline").toBeGreaterThanOrEqual(3)
  })

  test("clicking event expands JSON viewer", async ({ page }) => {
    await page.goto("/admin/conversations/conv-a1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // JSON viewer (pre tag) should not be visible initially
    const jsonViewer = page.locator("pre").first()
    await expect(jsonViewer).not.toBeVisible()

    // Click the first event button to expand it
    const firstEventBtn = page.locator(".glass-card button").first()
    await firstEventBtn.click()

    // JSON viewer should now be visible with event data
    const expandedJson = page.locator("pre").first()
    await expect(expandedJson).toBeVisible({ timeout: 3_000 })
    // Should contain JSON data from the extraction event
    await expect(expandedJson).toContainText("facts_count")
  })

  test("event count badge shows correct number", async ({ page }) => {
    await page.goto("/admin/conversations/conv-a1", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Badge: "3 events"
    await expect(page.getByText("3 events")).toBeVisible()
  })
})
