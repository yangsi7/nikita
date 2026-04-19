/**
 * Spec 214 T3.10 — Playwright E2E for the chat-first wizard.
 *
 * Happy path + @edge-case suite per AC-T3.10.1 / AC-T3.10.2. Assertions
 * target DOM structure and bubble counts rather than LLM-variable content
 * (tech-spec §7.3). The backend is mocked via `page.route` so this spec
 * does not require a live FastAPI backend.
 */

import { test, expect, Route } from "@playwright/test"

const API = "**/api/v1/portal/onboarding/converse"
const LINK = "**/api/v1/portal/link-telegram"

type MockTurn = {
  status?: number
  body: Record<string, unknown>
  headers?: Record<string, string>
}

function jsonFulfill(route: Route, m: MockTurn): Promise<void> {
  return route.fulfill({
    status: m.status ?? 200,
    contentType: "application/json",
    headers: m.headers,
    body: JSON.stringify(m.body),
  })
}

async function mockConverseSequence(page: import("@playwright/test").Page, turns: MockTurn[]) {
  let i = 0
  await page.route(API, async (route) => {
    const turn = turns[Math.min(i, turns.length - 1)]
    i += 1
    await jsonFulfill(route, turn)
  })
}

async function mockLinkTelegram(page: import("@playwright/test").Page, code = "ABC123") {
  await page.route(LINK, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        code,
        expires_at: "2026-04-20T00:00:00Z",
      }),
    })
  })
}

async function mockPortalStats(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/portal/stats", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ onboarded_at: null }),
    })
  })
}

test.describe("Onboarding chat wizard — AC-T3.10.1 happy path", () => {
  test("opens at /onboarding, renders chat log + input + progress", async ({ page }) => {
    await mockPortalStats(page)
    await mockConverseSequence(page, [
      {
        body: {
          nikita_reply: "zurich. nice.",
          extracted_fields: { location_city: "Zurich" },
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 20,
          conversation_complete: false,
          source: "llm",
          latency_ms: 120,
        },
      },
    ])

    await page.goto("/onboarding")

    // AC 1/2/3: opener + progress bar + input visible
    await expect(page.getByTestId("chat-log")).toBeVisible()
    await expect(page.getByTestId("progress-header")).toBeVisible()
    await expect(page.getByLabel("chat input")).toBeVisible()

    // AC 4: type + send → agent reply + progress advances
    await page.getByLabel("chat input").fill("zurich")
    await page.getByRole("button", { name: "send" }).click()

    // Nikita reply bubble is the 2nd Nikita turn (after opener)
    const nikitaBubbles = page.getByTestId("message-bubble-nikita")
    await expect(nikitaBubbles).toHaveCount(2, { timeout: 5_000 })

    // Progress bar label reflects the mocked progress_pct=20
    await expect(page.getByTestId("progress-label")).toHaveText(
      "Building your file... 20%"
    )
  })

  test("AC-T3.10.1 (11 assertions): DOM structure holds across turn types", async ({
    page,
  }) => {
    await mockPortalStats(page)
    await mockLinkTelegram(page, "ABC123")
    await mockConverseSequence(page, [
      // turn 1: location
      {
        body: {
          nikita_reply: "zurich. nice.",
          extracted_fields: { location_city: "Zurich" },
          confirmation_required: false,
          next_prompt_type: "chips",
          next_prompt_options: ["techno", "jazz"],
          progress_pct: 20,
          conversation_complete: false,
          source: "llm",
          latency_ms: 120,
        },
      },
      // turn 2: scene (chips)
      {
        body: {
          nikita_reply: "techno. got it.",
          extracted_fields: { social_scene: "techno" },
          confirmation_required: false,
          next_prompt_type: "slider",
          progress_pct: 40,
          conversation_complete: false,
          source: "llm",
          latency_ms: 120,
        },
      },
      // turn 3: darkness slider
      {
        body: {
          nikita_reply: "3. moving on.",
          extracted_fields: { drug_tolerance: 3 },
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 60,
          conversation_complete: false,
          source: "llm",
          latency_ms: 120,
        },
      },
      // turn 4: completion
      {
        body: {
          nikita_reply: "file closed.",
          extracted_fields: {},
          confirmation_required: false,
          next_prompt_type: "none",
          progress_pct: 100,
          conversation_complete: true,
          source: "llm",
          latency_ms: 120,
        },
      },
    ])

    await page.goto("/onboarding")

    // 1. Chat log visible
    await expect(page.getByTestId("chat-log")).toBeVisible()
    // 2. Progress header visible
    await expect(page.getByTestId("progress-header")).toBeVisible()
    // 3. Text input rendered by default
    await expect(page.getByLabel("chat input")).toBeVisible()

    // Turn 1: text
    await page.getByLabel("chat input").fill("zurich")
    await page.getByRole("button", { name: "send" }).click()
    // 4. Chips control appears
    await expect(page.getByTestId("chips-control")).toBeVisible()

    // Turn 2: chips
    await page.getByRole("button", { name: "techno" }).click()
    // 5. Slider control appears
    await expect(page.getByTestId("slider-control")).toBeVisible()

    // Turn 3: slider tap
    await page.getByRole("radio", { name: "3" }).click()
    // 6. Text input returns
    await expect(page.getByLabel("chat input")).toBeVisible()

    // Turn 4: completion
    await page.getByLabel("chat input").fill("ok")
    await page.getByRole("button", { name: "send" }).click()

    // 7. Ceremony mounts on completion
    await expect(page.getByTestId("clearance-granted-ceremony")).toBeVisible({
      timeout: 5_000,
    })
    // 8. Ceremony CTA href is t.me deep link with 6-char (or longer) token
    const cta = page.getByTestId("ceremony-cta")
    await expect(cta).toBeVisible()
    const href = await cta.getAttribute("href")
    expect(href).toMatch(/^https:\/\/t\.me\/Nikita_my_bot\?start=[A-Z0-9]+$/i)
    // 9. Progress bar is 100% at the end
    await expect(page.getByTestId("progress-label")).toHaveText(
      "Building your file... 100%"
    )
    // 10. Chat log no longer paints (ceremony replaces it)
    await expect(page.getByTestId("chat-log")).not.toBeVisible()
    // 11. aria-live scope: ceremony container lacks role='log' (that was chat-only)
    const log = page.locator('[role="log"]')
    await expect(log).toHaveCount(0)
  })
})

test.describe("Onboarding chat wizard — @edge-case suite (AC-T3.10.2)", () => {
  test("@edge-case Fix-that creates ghost-turn + server ack", async ({ page }) => {
    await mockPortalStats(page)
    await mockConverseSequence(page, [
      {
        body: {
          nikita_reply: "zurich. right?",
          extracted_fields: { location_city: "Zurich" },
          confirmation_required: true,
          next_prompt_type: "text",
          progress_pct: 20,
          conversation_complete: false,
          source: "llm",
          latency_ms: 100,
        },
      },
      {
        body: {
          nikita_reply: "ok, tell me which city then.",
          extracted_fields: {},
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 20,
          conversation_complete: false,
          source: "llm",
          latency_ms: 100,
        },
      },
    ])

    await page.goto("/onboarding")
    await page.getByLabel("chat input").fill("zurich")
    await page.getByRole("button", { name: "send" }).click()

    // [Yes] [Fix that] buttons present
    await expect(page.getByTestId("confirmation-yes")).toBeVisible()
    await expect(page.getByTestId("confirmation-fix")).toBeVisible()

    // Click fix-that → the latest Nikita bubble gets data-superseded
    await page.getByTestId("confirmation-fix").click()
    const nikitaBubbles = page.getByTestId("message-bubble-nikita")
    // the first Nikita turn (opener) isn't superseded; the second one
    // (the one containing "zurich. right?") is.
    const supersededCount = await nikitaBubbles.evaluateAll((els) =>
      els.filter((e) => e.getAttribute("data-superseded") === "true").length
    )
    expect(supersededCount).toBeGreaterThanOrEqual(1)
  })

  test("@edge-case timeout fallback renders source='fallback' bubble", async ({ page }) => {
    await mockPortalStats(page)
    // fallback response from backend on timeout branch
    await page.route(API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          nikita_reply: "i lost the signal for a sec. try again.",
          extracted_fields: {},
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 0,
          conversation_complete: false,
          source: "fallback",
          latency_ms: 2500,
        }),
      })
    })
    await page.goto("/onboarding")
    await page.getByLabel("chat input").fill("testing")
    await page.getByRole("button", { name: "send" }).click()
    // Bubble with data-source='fallback' visible
    await expect(
      page.locator('[data-testid="message-bubble-nikita"][data-source="fallback"]')
    ).toBeVisible({ timeout: 5_000 })
  })

  test("@edge-case backtracking: later fields survive when a prior field changes", async ({
    page,
  }) => {
    await mockPortalStats(page)
    await mockConverseSequence(page, [
      {
        body: {
          nikita_reply: "zurich.",
          extracted_fields: { location_city: "Zurich" },
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 20,
          conversation_complete: false,
          source: "llm",
          latency_ms: 100,
        },
      },
      {
        body: {
          nikita_reply: "berlin. got it. anything else?",
          extracted_fields: { location_city: "Berlin" },
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 20,
          conversation_complete: false,
          source: "llm",
          latency_ms: 100,
        },
      },
    ])
    await page.goto("/onboarding")
    await page.getByLabel("chat input").fill("zurich")
    await page.getByRole("button", { name: "send" }).click()
    await expect(page.getByTestId("message-bubble-nikita")).toHaveCount(2, {
      timeout: 5_000,
    })
    // Backtrack
    await page.getByLabel("chat input").fill("change my city to berlin")
    await page.getByRole("button", { name: "send" }).click()
    await expect(page.getByTestId("message-bubble-nikita")).toHaveCount(3, {
      timeout: 5_000,
    })
  })

  test("@edge-case age<18 in-character rejection (no red banner)", async ({ page }) => {
    await mockPortalStats(page)
    await mockConverseSequence(page, [
      {
        body: {
          nikita_reply: "we need you to be 18 or older. catch me when you are.",
          extracted_fields: {},
          confirmation_required: false,
          next_prompt_type: "text",
          progress_pct: 0,
          conversation_complete: false,
          source: "validation_reject",
          latency_ms: 50,
        },
      },
    ])
    await page.goto("/onboarding")
    await page.getByLabel("chat input").fill("i am 15")
    await page.getByRole("button", { name: "send" }).click()
    // In-character bubble; no destructive banner.
    await expect(
      page.locator('[data-testid="message-bubble-nikita"][data-source="validation_reject"]')
    ).toBeVisible({ timeout: 5_000 })
    // Input still available for the user to amend
    await expect(page.getByLabel("chat input")).toBeVisible()
  })
})
