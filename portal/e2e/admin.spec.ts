import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectDataLoaded } from "./fixtures/assertions"

/**
 * Admin dashboard E2E tests — route rendering with deterministic mock data.
 */

test.beforeEach(async ({ context }) => {
  await context.addCookies([{ name: "e2e-role", value: "admin", domain: "localhost", path: "/" }])
})

test.describe("Admin Routes — Smoke Tests", () => {
  const adminRoutes = [
    { path: "/admin", name: "Admin Overview" },
    { path: "/admin/users", name: "User Management" },
    { path: "/admin/pipeline", name: "Pipeline Health" },
    { path: "/admin/voice", name: "Voice Monitoring" },
    { path: "/admin/text", name: "Text Monitoring" },
    { path: "/admin/jobs", name: "Job Status" },
    { path: "/admin/prompts", name: "Prompt History" },
    { path: "/admin/systems", name: "Systems Tour" },
  ]

  for (const route of adminRoutes) {
    test(`${route.name} (${route.path}) loads with content`, async ({ page }) => {
      await mockApiRoutes(page)
      await page.goto(route.path, { waitUntil: "networkidle" })
      await expectDataLoaded(page)
    })
  }
})

test.describe("Admin Routes — Structure", () => {
  test("admin sidebar has all navigation items", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Verify all admin nav links exist in sidebar
    const navItems = ["Overview", "Users", "Voice", "Conversations", "Pipeline", "Jobs", "Prompts", "Systems"]
    for (const item of navItems) {
      await expect(
        page.locator(`text=${item}`).first(),
        `Sidebar should contain "${item}" link`
      ).toBeVisible()
    }
  })

  test("Systems Tour renders all five section headings and every art endpoint responds", async ({ page }) => {
    await mockApiRoutes(page)

    await page.goto("/admin/systems", { waitUntil: "domcontentloaded" })

    await expect(
      page.getByRole("heading", { level: 1, name: "Systems Tour" }),
    ).toBeVisible()

    const expectedSections = [
      "The Timing Mind",
      "Memory as Network",
      "The Ecosystem Inside",
      "Your Model Diverges",
      "Chapters as Fractal",
    ]
    for (const title of expectedSections) {
      await expect(
        page.getByRole("heading", { level: 2, name: title }),
        `Systems Tour should contain "${title}"`,
      ).toBeVisible()
    }

    // Hit every art endpoint directly — independent of iframe lazy-load
    // timing and viewport sensitivity. Ensures all 5 slugs respond with
    // the correct Content-Type and CSP sandbox header.
    const slugs = [
      "fluid-dynamics",
      "physarum-slime-mold",
      "ecosystem",
      "double-pendulum-chaos",
      "fractal-flames",
    ]
    for (const slug of slugs) {
      const resp = await page.request.get(`/admin/systems/art/${slug}`)
      expect(resp.status(), `GET /admin/systems/art/${slug}`).toBe(200)
      expect(resp.headers()["content-type"]).toMatch(/text\/html/)
      expect(resp.headers()["content-security-policy"]).toContain("sandbox")
      expect(resp.headers()["x-content-type-options"]).toBe("nosniff")
      expect(resp.headers()["cache-control"]).toMatch(/private/)
    }
  })
})
