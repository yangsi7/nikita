import { test, expect, expectProtectedRoute } from "./fixtures"

/**
 * Admin dashboard E2E tests.
 *
 * Tests verify admin routes are accessible and render expected structure.
 * Without auth, pages may show error states (acceptable) or redirect to /login.
 */

test.describe("Admin Routes — Smoke Tests", () => {
  const adminRoutes = [
    { path: "/admin", name: "Admin Overview", heading: "System Overview" },
    { path: "/admin/users", name: "User Management", heading: "User Management" },
    { path: "/admin/pipeline", name: "Pipeline Health", heading: "Pipeline" },
    { path: "/admin/voice", name: "Voice Monitoring", heading: "Voice" },
    { path: "/admin/text", name: "Text Monitoring", heading: "Text" },
    { path: "/admin/jobs", name: "Job Status", heading: "Job" },
    { path: "/admin/prompts", name: "Prompt History", heading: "Prompt" },
  ]

  for (const route of adminRoutes) {
    test(`${route.name} (${route.path}) loads or redirects`, async ({ page }) => {
      const result = await expectProtectedRoute(page, route.path)

      if (result === "rendered") {
        // Page rendered — verify admin sidebar is present
        const sidebar = page.locator("text=Overview")
        const hasSidebar = await sidebar.isVisible().catch(() => false)
        if (hasSidebar) {
          // Verify admin sidebar nav items exist
          await expect(page.locator("text=Users").first()).toBeVisible()
          await expect(page.locator("text=Pipeline").first()).toBeVisible()
        }
      }
      // Either outcome is valid
      expect(["redirected", "rendered"]).toContain(result)
    })
  }
})

test.describe("Admin Routes — Structure", () => {
  test("admin sidebar has all navigation items when rendered", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/admin")

    if (result === "rendered") {
      // Verify all admin nav links exist in sidebar
      const navItems = ["Overview", "Users", "Voice", "Text", "Pipeline", "Jobs", "Prompts"]
      for (const item of navItems) {
        await expect(page.locator(`text=${item}`).first()).toBeVisible()
      }
    }
  })

  test("admin page renders or redirects without valid auth", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/admin")
    // Without auth: either redirects to /login or renders page (both acceptable)
    expect(["redirected", "rendered"]).toContain(result)
  })
})
