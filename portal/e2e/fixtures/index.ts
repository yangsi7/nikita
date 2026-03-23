import { test as base, expect, type Page } from "@playwright/test"

export const test = base
export { expect }

export { mockApiRoutes } from "./api-mocks"

export {
  expectTableRows,
  expectChartRendered,
  expectCardContent,
  expectNoEmptyState,
  expectDataLoaded,
} from "./assertions"

export {
  mockUser, mockMetrics, mockScoreHistory, mockDetailedScoreHistory,
  mockEngagement, mockDecay, mockConversations, mockConversationDetail,
  mockVices, mockDiary, mockSettings, mockInsights,
  mockNikitaMind, mockNikitaCircle, mockNikitaDay, mockNikitaStories,
  mockAdminStats, mockAdminUsers, mockAdminUserDetail,
  mockPipelineHealth, mockPipelineEvents, mockJobs, mockPipelineRuns,
  mockAdminConversations, mockGeneratedPrompts, mockVoiceConversations,
  mockThoughts, mockLifeEvents,
  mockOnboardingProfile, mockNewUserStats, mockOnboardedUserStats,
} from "./factories"

// ─── Legacy helpers (kept for auth-flow, login, accessibility tests) ───

/**
 * Assert protected route is guarded.
 * With E2E auth bypass active, pages always render (never redirect to /login).
 * This helper is kept for backward compatibility with auth-flow tests.
 */
export async function expectProtectedRoute(page: Page, path: string): Promise<"redirected" | "rendered"> {
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 30_000 })
  await page.waitForTimeout(2_000)

  const url = page.url()
  if (url.includes("/login")) {
    return "redirected"
  }

  const body = page.locator("body")
  await expect(body).toBeVisible()
  return "rendered"
}

/**
 * Assert the login page has expected elements.
 */
export async function assertLoginPageElements(page: Page) {
  await expect(page.getByText("Nikita")).toBeVisible()
  await expect(page.getByText("Sign in to your dashboard")).toBeVisible()
  await expect(page.getByPlaceholder("you@example.com")).toBeVisible()
  await expect(page.getByRole("button", { name: /send magic link/i })).toBeVisible()
}

/**
 * Wait for page to settle (loading states to resolve).
 */
export async function waitForPageSettled(page: Page, timeoutMs = 5_000) {
  try {
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="skeleton"], [class*="Skeleton"]').length === 0,
      { timeout: timeoutMs }
    )
  } catch {
    // Timeout is acceptable
  }
}
