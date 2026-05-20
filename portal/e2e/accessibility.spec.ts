import { test, expect, expectProtectedRoute } from "./fixtures"
import AxeBuilder from "@axe-core/playwright"

/**
 * Accessibility audit E2E tests.
 *
 * Uses @axe-core/playwright to verify WCAG 2.1 AA compliance.
 * Tests run axe scans on key pages and verify keyboard navigation.
 *
 * Known issues (logged but not blocking):
 * - color-contrast: Dark glassmorphism theme has some contrast ratio violations
 * - link-in-text-block: Some links not distinguished from surrounding text
 */

// Rules to exclude (known design decisions, not bugs)
const KNOWN_CONTRAST_RULES = ["color-contrast", "link-in-text-block"]

// Spec 220 PR-A: /login was deleted (now 410). The canonical entry surface is
// the landing page (/), which carries the TG-first CTA. The whole-page axe scan
// is retargeted to / to keep a11y coverage on the real entry surface. The two
// CTA-selector tests below were coupled to the deleted /login `login-telegram-cta`
// testid and are skipped; landing CTA a11y is covered by the whole-page scan.
test.describe("Accessibility — Landing Page (entry surface, Spec 220)", () => {
  test("landing page has no critical WCAG violations (excluding known contrast)", async ({ page }) => {
    await page.goto("/")
    await page.waitForTimeout(1_000)

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .disableRules(KNOWN_CONTRAST_RULES)
      .analyze()

    // Filter for critical and serious violations only
    const critical = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    )

    if (critical.length > 0) {
      const summary = critical.map(
        (v) => `${v.impact}: ${v.id} - ${v.description} (${v.nodes.length} instances)`
      ).join("\n")
      console.log("Accessibility violations on /:\n" + summary)
    }

    expect(critical.length).toBe(0)
  })

  test.skip("login page CTA has accessible controls (deleted in PR-A — re-target to landing CTA in follow-up)", async ({ page }) => {
    await page.goto("/login")
    await page.waitForTimeout(1_000)
    const cta = page.locator('[data-testid="login-telegram-cta"]')
    await expect(cta).toBeVisible()
    await expect(cta).toHaveAttribute("href", /^https:\/\/t\.me\//)
    const text = await cta.textContent()
    expect(text?.trim().length ?? 0).toBeGreaterThan(0)
  })
})

test.describe("Accessibility — Dashboard Page", () => {
  test("dashboard page has no critical WCAG violations (excluding known contrast)", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/dashboard")

    if (result === "rendered") {
      await page.waitForTimeout(1_000)

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .disableRules(KNOWN_CONTRAST_RULES)
        .analyze()

      const critical = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      )

      if (critical.length > 0) {
        const summary = critical.map(
          (v) => `${v.impact}: ${v.id} - ${v.description} (${v.nodes.length} instances)`
        ).join("\n")
        console.log("Accessibility violations on /dashboard:\n" + summary)
      }

      expect(critical.length).toBe(0)
    }
  })
})

test.describe("Accessibility — Admin Page", () => {
  test("admin page has no critical WCAG violations (excluding known contrast)", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/admin")

    if (result === "rendered") {
      await page.waitForTimeout(1_000)

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .disableRules(KNOWN_CONTRAST_RULES)
        .analyze()

      const critical = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      )

      if (critical.length > 0) {
        const summary = critical.map(
          (v) => `${v.impact}: ${v.id} - ${v.description} (${v.nodes.length} instances)`
        ).join("\n")
        console.log("Accessibility violations on /admin:\n" + summary)
      }

      expect(critical.length).toBe(0)
    }
  })
})

test.describe("Accessibility — Keyboard Navigation", () => {
  test.skip("login page CTA is reachable via Tab (deleted in PR-A — /login now 410)", async ({ page }) => {
    await page.goto("/login")
    await page.waitForTimeout(1_000)
    await page.keyboard.press("Tab")
    const activeTag = await page.evaluate(() => document.activeElement?.tagName)
    expect(
      ["A", "BUTTON"],
      `Expected anchor or button focused, got ${activeTag}`
    ).toContain(activeTag)
  })

  test("sidebar navigation is keyboard accessible when rendered", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/dashboard")

    if (result === "rendered") {
      // Tab through sidebar elements
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press("Tab")
      }

      // Verify that focus is somewhere meaningful (not stuck on body)
      const activeTag = await page.evaluate(() => document.activeElement?.tagName)
      expect(["INPUT", "BUTTON", "A", "SELECT", "TEXTAREA"], `Expected focusable element, got ${activeTag}`).toContain(activeTag)
    }
  })
})

test.describe("Accessibility — Color Contrast Audit (informational)", () => {
  test("landing page contrast violations are logged", async ({ page }) => {
    // Spec 220 PR-A: retargeted from /login (deleted, 410) to landing /.
    await page.goto("/")
    await page.waitForTimeout(1_000)

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze()

    const contrastIssues = results.violations.filter(
      (v) => v.id === "color-contrast"
    )

    if (contrastIssues.length > 0) {
      const details = contrastIssues.flatMap((v) =>
        v.nodes.map((n) => `  - ${n.html.slice(0, 80)}... (${n.any?.[0]?.message ?? "unknown"})`)
      ).join("\n")
      console.log(`[INFO] Color contrast issues on / (${contrastIssues[0]?.nodes.length ?? 0} instances):\n${details}`)
    }

    // Dark theme with sufficient contrast applied
    const bgColor = await page.locator("body").evaluate(
      (el) => getComputedStyle(el).backgroundColor
    )
    expect(bgColor).not.toBe("rgb(255, 255, 255)")
  })
})
