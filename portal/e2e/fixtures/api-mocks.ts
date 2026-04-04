/**
 * Browser-side API route mocking via page.route().
 * Intercepts /api/v1/portal/* and /api/v1/admin/* calls with deterministic factory data.
 *
 * URL pattern: ${NEXT_PUBLIC_API_URL}/api/v1/{path}
 *   - Player: /api/v1/portal/stats, /portal/engagement, etc.
 *   - Admin: /api/v1/admin/stats, /admin/users, etc.
 */

import type { Page } from "@playwright/test"
import {
  mockUser, mockScoreHistory, mockEngagement, mockDecay,
  mockConversations, mockConversationDetail, mockVices, mockDiary,
  mockSettings, mockNikitaMind, mockNikitaCircle, mockNikitaDay,
  mockNikitaStories, mockInsights, mockThoughts, mockLifeEvents,
  mockAdminStats, mockAdminUsers, mockAdminUserDetail,
  mockPipelineHealth, mockPipelineEvents, mockJobs, mockPipelineRuns,
  mockAdminConversations, mockGeneratedPrompts, mockVoiceConversations,
  mockDetailedScoreHistory,
} from "./factories"

function json(data: unknown) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(data),
  }
}

/**
 * Register all API route mocks on a Playwright page.
 * Call this BEFORE navigating to any page.
 */
export async function mockApiRoutes(page: Page) {
  // ─── Catch-all FIRST (lowest priority — Playwright: last-registered wins) ──
  await page.route("**/api/v1/**", (route) => {
    return route.fulfill(json({ detail: "Mock not configured for this route" }))
  })

  // ─── Supabase auth (client-side checks) ────────────────────────
  await page.route("**/auth/v1/user", (route) => {
    return route.fulfill(json({
      id: "e2e-player-id",
      email: "e2e-player@test.local",
      user_metadata: {},
      aud: "authenticated",
    }))
  })

  // ─── Player endpoints (/api/v1/portal/*) ───────────────────────
  await page.route("**/api/v1/portal/stats", (route) => route.fulfill(json(mockUser())))
  await page.route("**/api/v1/portal/score-history?*", (route) => route.fulfill(json(mockScoreHistory())))
  await page.route("**/api/v1/portal/score-history/detailed*", (route) => route.fulfill(json(mockDetailedScoreHistory())))
  await page.route("**/api/v1/portal/engagement", (route) => route.fulfill(json(mockEngagement())))
  await page.route("**/api/v1/portal/decay", (route) => route.fulfill(json(mockDecay())))
  await page.route("**/api/v1/portal/vices", (route) => route.fulfill(json(mockVices())))
  await page.route("**/api/v1/portal/conversations*", (route) => {
    const url = route.request().url()
    // Detail route: /portal/conversations/{id}
    if (/\/conversations\/[^/?]+$/.test(url)) {
      const id = url.split("/conversations/")[1]?.split("?")[0] ?? "conv-1"
      return route.fulfill(json(mockConversationDetail({ id })))
    }
    return route.fulfill(json(mockConversations()))
  })
  await page.route("**/api/v1/portal/daily-summaries*", (route) => route.fulfill(json(mockDiary())))
  await page.route("**/api/v1/portal/settings", (route) => route.fulfill(json(mockSettings())))
  await page.route("**/api/v1/portal/insights*", (route) => route.fulfill(json(mockInsights())))

  // Nikita world endpoints
  await page.route("**/api/v1/portal/emotional-state/history*", (route) => route.fulfill(json({ points: [], total_count: 0 })))
  await page.route("**/api/v1/portal/emotional-state", (route) => route.fulfill(json(mockNikitaMind())))
  await page.route("**/api/v1/portal/social-circle", (route) => route.fulfill(json(mockNikitaCircle())))
  await page.route("**/api/v1/portal/psyche-tips", (route) => route.fulfill(json(mockNikitaDay())))
  await page.route("**/api/v1/portal/narrative-arcs*", (route) => route.fulfill(json(mockNikitaStories())))
  await page.route("**/api/v1/portal/thoughts*", (route) => route.fulfill(json(mockThoughts())))
  await page.route("**/api/v1/portal/life-events*", (route) => route.fulfill(json(mockLifeEvents())))
  await page.route("**/api/v1/portal/threads*", (route) => route.fulfill(json({ threads: [], total_count: 0, open_count: 0 })))

  // ─── Admin endpoints (/api/v1/admin/*) ─────────────────────────
  // NOTE: Playwright's single '*' does NOT match '/' — use '/**' or a function matcher
  // for routes that have sub-paths like /users/{id} or /conversations/{id}/events.
  await page.route("**/api/v1/admin/stats", (route) => route.fulfill(json(mockAdminStats())))
  // Users: /admin/users (list) and /admin/users/{id} (detail)
  await page.route(
    (url) => url.toString().includes("/api/v1/admin/users"),
    (route) => {
      const url = route.request().url()
      const pathWithoutQuery = url.split("?")[0]
      // Detail route: ends with /users/{id} (no further sub-path)
      if (/\/users\/[^/]+$/.test(pathWithoutQuery)) {
        return route.fulfill(json(mockAdminUserDetail()))
      }
      return route.fulfill(json(mockAdminUsers()))
    }
  )
  await page.route("**/api/v1/admin/unified-pipeline/health", (route) => route.fulfill(json(mockPipelineHealth())))
  await page.route("**/api/v1/admin/events*", (route) => route.fulfill(json(mockPipelineEvents())))
  await page.route("**/api/v1/admin/processing-stats", (route) => route.fulfill(json({ total_processed: 100, avg_processing_time_ms: 500 })))
  // Conversations: /admin/conversations (list), /admin/conversations/{id} (detail), /admin/conversations/{id}/events
  await page.route(
    (url) => url.toString().includes("/api/v1/admin/conversations"),
    (route) => {
      const url = route.request().url()
      if (/\/conversations\/[^/?]+\/events/.test(url)) {
        return route.fulfill(json({ conversation_id: "conv-a1", events: [], count: 0 }))
      }
      if (/\/conversations\/[^/?]+$/.test(url)) {
        const id = url.split("/conversations/")[1]?.split("?")[0] ?? "conv-a1"
        return route.fulfill(json(mockConversationDetail({ id })))
      }
      return route.fulfill(json(mockAdminConversations()))
    }
  )
  await page.route("**/api/v1/admin/prompts*", (route) => route.fulfill(json(mockGeneratedPrompts())))
  await page.route("**/api/v1/admin/voice*", (route) => route.fulfill(json(mockVoiceConversations())))
  await page.route("**/api/v1/tasks/*", (route) => route.fulfill(json(mockJobs())))

  // ─── Onboarding endpoints ────────────────────────────────────
  await page.route("**/api/v1/onboarding/profile", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill(json({ status: "ok", message: "Profile saved, game starting..." }))
    } else {
      await route.fallback()
    }
  })

}
