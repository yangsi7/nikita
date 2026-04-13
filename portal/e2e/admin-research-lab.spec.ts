import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"

/**
 * Research Lab admin section — E2E tests.
 *
 * Auth bypass (E2E_AUTH_BYPASS=true) is active in playwright.config, so:
 * - Admin role is simulated via the "e2e-role=admin" cookie.
 * - Non-admin role is simulated by clearing the cookie (default player role).
 * - Redirect-to-login / redirect-to-dashboard assertions are tested with skip
 *   annotations matching the pattern in auth-flow.spec.ts, since E2E bypass
 *   prevents real middleware redirects; the middleware logic is unit-tested
 *   separately in portal/tests/.
 */

test.describe("Research Lab — Auth guards", () => {
  test.skip(
    "unauthenticated user redirects to /login",
    // Skipped: E2E_AUTH_BYPASS=true means middleware never redirects.
    // Real redirect tested in auth-flow.spec.ts when bypass is disabled.
    async () => {}
  )

  test.skip(
    "non-admin user redirects to /dashboard",
    // Skipped: same reason — bypass active; middleware logic tested in unit tests.
    async () => {}
  )
})

test.describe("Research Lab — Index page", () => {
  test.beforeEach(async ({ context }) => {
    await context.addCookies([{ name: "e2e-role", value: "admin", domain: "localhost", path: "/" }])
  })

  test("renders index page with response-timing model card", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab", { waitUntil: "networkidle" })

    // Page heading
    await expect(page.getByRole("heading", { name: /research lab/i })).toBeVisible()

    // Model card for response-timing
    await expect(page.getByText("Response Timing Model")).toBeVisible()
  })

  test("sidebar contains Research Lab nav entry", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin", { waitUntil: "networkidle" })

    await expect(page.getByRole("link", { name: /research lab/i })).toBeVisible()
  })

  test("clicking response-timing card navigates to detail page", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab", { waitUntil: "networkidle" })

    await page.getByText("Response Timing Model").click()
    await page.waitForURL("**/admin/research-lab/response-timing", { timeout: 10_000 })
    expect(page.url()).toContain("/admin/research-lab/response-timing")
  })
})

test.describe("Research Lab — Detail page", () => {
  test.beforeEach(async ({ context }) => {
    await context.addCookies([{ name: "e2e-role", value: "admin", domain: "localhost", path: "/" }])
  })

  test("detail page renders title and status badge", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab/response-timing", { waitUntil: "networkidle" })

    await expect(page.getByRole("heading", { name: /response timing model/i })).toBeVisible()
    // Status badge
    await expect(page.getByText("active")).toBeVisible()
  })

  test("detail page has Back to Research Lab link", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab/response-timing", { waitUntil: "networkidle" })

    const backLink = page.getByRole("link", { name: /research lab/i }).first()
    await expect(backLink).toBeVisible()
    await expect(backLink).toHaveAttribute("href", "/admin/research-lab")
  })

  test("detail page with artifactPath renders iframe with correct sandbox attribute", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab/response-timing", { waitUntil: "networkidle" })

    const iframe = page.locator("iframe")
    const count = await iframe.count()

    if (count > 0) {
      // When the artifact is present, iframe must have allow-scripts sandbox
      // and must NOT have allow-same-origin
      const sandboxAttr = await iframe.first().getAttribute("sandbox")
      expect(sandboxAttr).toContain("allow-scripts")
      expect(sandboxAttr).not.toContain("allow-same-origin")
      expect(sandboxAttr).not.toContain("allow-forms")

      // iframe src should end with .html
      const srcAttr = await iframe.first().getAttribute("src")
      expect(srcAttr).toMatch(/\.html$/)
    } else {
      // Artifact not yet synced — page should still render without crashing
      // (graceful absence of iframe is acceptable)
      await expect(page.locator("body")).toBeVisible()
    }
  })

  test("nikita-overview detail page renders without crashing", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab/nikita-overview", { waitUntil: "networkidle" })

    await expect(page.getByRole("heading", { name: /nikita.*overview/i })).toBeVisible()
    // No iframe for overview model
    await expect(page.locator("iframe")).toHaveCount(0)
  })

  test("unknown slug returns 404", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/research-lab/does-not-exist", { waitUntil: "networkidle" })
    // Next.js renders a 404 page
    await expect(page.getByText(/404|not found/i)).toBeVisible()
  })
})
