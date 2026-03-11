import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"
import { expectTableRows, expectDataLoaded } from "./fixtures/assertions"

/**
 * Admin mutation E2E tests — user list, detail navigation, filters, error states.
 * Uses mockApiRoutes for deterministic data.
 */

test.describe("Admin — User List", () => {
  test("admin users page renders table with user rows", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    await expectTableRows(page, "table-users", 1)
  })

  test("admin users table has correct column headers", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    const table = page.locator('[data-testid="table-users"]')
    await expect(table).toBeVisible()

    const expectedHeaders = ["User", "Score", "Chapter", "Engagement", "Status", "Last Active"]
    for (const header of expectedHeaders) {
      await expect(
        table.locator(`th:has-text("${header}")`),
        `Table should have "${header}" column header`
      ).toBeVisible()
    }
  })

  test("admin users page has search input", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    const searchInput = page.getByPlaceholder(/search/i)
    await expect(searchInput).toBeVisible()
    await searchInput.fill("test@example.com")
    const value = await searchInput.inputValue()
    expect(value).toBe("test@example.com")
  })

  test("admin users page has chapter and engagement filters", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    // Chapter and engagement select filters
    const selects = page.locator('[role="combobox"]')
    const count = await selects.count()
    expect(count, "Should have at least 2 filter dropdowns (chapter + engagement)").toBeGreaterThanOrEqual(2)
  })
})

test.describe("Admin — User Detail Navigation", () => {
  test("clicking a user row navigates to user detail", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/admin/users", { waitUntil: "networkidle" })
    await expectDataLoaded(page)

    const firstRow = page.locator('[data-testid="table-users"] tbody tr').first()
    await expect(firstRow).toBeVisible()
    await firstRow.click()
    await page.waitForURL("**/admin/users/**")
    expect(page.url()).toMatch(/\/admin\/users\//)
  })
})

test.describe("Admin — Error States", () => {
  test("admin users page shows error when API fails", async ({ page }) => {
    await page.route("**/api/v1/admin/users**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Database connection failed" }),
      })
    )
    // Mock auth endpoint so page loads
    await page.route("**/auth/v1/user", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "e2e-admin-id", email: "e2e-admin@test.local", user_metadata: { role: "admin" } }),
      })
    )

    await page.goto("/admin/users", { waitUntil: "networkidle" })

    const errorDisplay = page.locator('[data-testid="error-display"]')
    await expect(errorDisplay, "Error display should be shown when API returns 500").toBeVisible({ timeout: 10_000 })
  })
})

test.describe("Admin — Sidebar Navigation", () => {
  const adminPages = [
    { name: "Users", path: "/admin/users" },
    { name: "Pipeline", path: "/admin/pipeline" },
    { name: "Jobs", path: "/admin/jobs" },
    { name: "Prompts", path: "/admin/prompts" },
  ]

  for (const pg of adminPages) {
    test(`admin sidebar navigates to ${pg.name}`, async ({ page }) => {
      await mockApiRoutes(page)
      await page.goto("/admin", { waitUntil: "networkidle" })
      await expectDataLoaded(page)

      const link = page.locator(`a[href="${pg.path}"]`).first()
      await expect(link).toBeVisible({ timeout: 5_000 })
      await link.click()
      await page.waitForURL(`**${pg.path}`)
      expect(page.url()).toContain(pg.path)
    })
  }
})
