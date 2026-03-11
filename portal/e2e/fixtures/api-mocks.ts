/**
 * Browser-side API route mocking via page.route().
 * Intercepts /api/v1/* and Supabase REST calls with deterministic factory data.
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
  // Player endpoints
  await page.route("**/api/v1/users/me", (route) => route.fulfill(json(mockUser())))
  await page.route("**/api/v1/users/me/stats", (route) => route.fulfill(json(mockUser())))
  await page.route("**/api/v1/users/me/metrics", (route) => route.fulfill(json(mockUser().metrics)))
  await page.route("**/api/v1/users/me/score-history*", (route) => route.fulfill(json(mockScoreHistory())))
  await page.route("**/api/v1/users/me/detailed-score-history*", (route) => route.fulfill(json(mockDetailedScoreHistory())))
  await page.route("**/api/v1/users/me/engagement", (route) => route.fulfill(json(mockEngagement())))
  await page.route("**/api/v1/users/me/decay", (route) => route.fulfill(json(mockDecay())))
  await page.route("**/api/v1/users/me/conversations*", (route) => {
    const url = route.request().url()
    // Detail route: /conversations/{id}
    if (/\/conversations\/[^/?]+$/.test(url)) {
      const id = url.split("/conversations/")[1]?.split("?")[0] ?? "conv-1"
      return route.fulfill(json(mockConversationDetail({ id })))
    }
    return route.fulfill(json(mockConversations()))
  })
  await page.route("**/api/v1/users/me/vices", (route) => route.fulfill(json(mockVices())))
  await page.route("**/api/v1/users/me/diary*", (route) => route.fulfill(json(mockDiary())))
  await page.route("**/api/v1/users/me/settings", (route) => route.fulfill(json(mockSettings())))
  await page.route("**/api/v1/users/me/insights*", (route) => route.fulfill(json(mockInsights())))

  // Nikita world endpoints
  await page.route("**/api/v1/users/me/emotional-state", (route) => route.fulfill(json(mockNikitaMind())))
  await page.route("**/api/v1/users/me/emotional-state/history*", (route) => route.fulfill(json({ points: [], total_count: 0 })))
  await page.route("**/api/v1/users/me/social-circle", (route) => route.fulfill(json(mockNikitaCircle())))
  await page.route("**/api/v1/users/me/psyche-tips", (route) => route.fulfill(json(mockNikitaDay())))
  await page.route("**/api/v1/users/me/narrative-arcs", (route) => route.fulfill(json(mockNikitaStories())))
  await page.route("**/api/v1/users/me/thoughts*", (route) => route.fulfill(json(mockThoughts())))
  await page.route("**/api/v1/users/me/life-events*", (route) => route.fulfill(json(mockLifeEvents())))
  await page.route("**/api/v1/users/me/threads*", (route) => route.fulfill(json({ threads: [], total_count: 0, open_count: 0 })))

  // Admin endpoints
  await page.route("**/api/v1/admin/stats", (route) => route.fulfill(json(mockAdminStats())))
  await page.route("**/api/v1/admin/users*", (route) => {
    const url = route.request().url()
    // Detail route: /admin/users/{id}
    if (/\/users\/[^/?]+$/.test(url) && !url.includes("/users?")) {
      return route.fulfill(json(mockAdminUserDetail()))
    }
    return route.fulfill(json(mockAdminUsers()))
  })
  await page.route("**/api/v1/admin/pipeline/health", (route) => route.fulfill(json(mockPipelineHealth())))
  await page.route("**/api/v1/admin/pipeline/events*", (route) => route.fulfill(json(mockPipelineEvents())))
  await page.route("**/api/v1/admin/pipeline/runs*", (route) => route.fulfill(json(mockPipelineRuns())))
  await page.route("**/api/v1/admin/pipeline/failures*", (route) => route.fulfill(json([])))
  await page.route("**/api/v1/admin/jobs", (route) => route.fulfill(json(mockJobs())))
  await page.route("**/api/v1/admin/conversations*", (route) => {
    const url = route.request().url()
    if (/\/conversations\/[^/?]+$/.test(url)) {
      const id = url.split("/conversations/")[1]?.split("?")[0] ?? "conv-a1"
      return route.fulfill(json(mockConversationDetail({ id })))
    }
    return route.fulfill(json(mockAdminConversations()))
  })
  await page.route("**/api/v1/admin/prompts*", (route) => route.fulfill(json(mockGeneratedPrompts())))
  await page.route("**/api/v1/admin/voice*", (route) => route.fulfill(json(mockVoiceConversations())))

  // Supabase auth endpoint mock (for client-side auth checks)
  await page.route("**/auth/v1/user", (route) => {
    return route.fulfill(json({
      id: "e2e-player-id",
      email: "e2e-player@test.local",
      user_metadata: {},
      aud: "authenticated",
    }))
  })

  // Catch-all for any unmatched /api/v1 routes
  await page.route("**/api/v1/**", (route) => {
    return route.fulfill(json({ detail: "Mock not configured for this route" }))
  })
}
