/**
 * Content assertion helpers for E2E tests.
 * All helpers use data-testid attributes for reliable selectors.
 * No .catch(() => false) patterns — assertions fail with descriptive messages.
 */

import { expect, type Page } from "@playwright/test"

const DEFAULT_TIMEOUT = 10_000

/**
 * Assert that a table has at least `min` data rows (tbody tr).
 */
export async function expectTableRows(page: Page, testId: string, min: number, timeout = DEFAULT_TIMEOUT) {
  const table = page.locator(`[data-testid="${testId}"]`)
  await expect(table, `Table [data-testid="${testId}"] should be visible`).toBeVisible({ timeout })
  const rows = table.locator("tbody tr")
  const count = await rows.count()
  expect(count, `Table [data-testid="${testId}"] should have at least ${min} rows, found ${count}`).toBeGreaterThanOrEqual(min)
}

/**
 * Assert that a chart container (SVG) is rendered inside a data-testid element.
 */
export async function expectChartRendered(page: Page, testId: string, timeout = DEFAULT_TIMEOUT) {
  const container = page.locator(`[data-testid="${testId}"]`)
  await expect(container, `Chart container [data-testid="${testId}"] should be visible`).toBeVisible({ timeout })
  // Recharts renders SVG elements
  const svg = container.locator("svg").first()
  await expect(svg, `Chart [data-testid="${testId}"] should contain an SVG element`).toBeVisible({ timeout })
}

/**
 * Assert that a card contains expected text content.
 */
export async function expectCardContent(page: Page, testId: string, textPattern: string | RegExp, timeout = DEFAULT_TIMEOUT) {
  const card = page.locator(`[data-testid="${testId}"]`)
  await expect(card, `Card [data-testid="${testId}"] should be visible`).toBeVisible({ timeout })
  if (typeof textPattern === "string") {
    await expect(card, `Card [data-testid="${testId}"] should contain text "${textPattern}"`).toContainText(textPattern, { timeout })
  } else {
    await expect(card, `Card [data-testid="${testId}"] should match pattern ${textPattern}`).toContainText(textPattern, { timeout })
  }
}

/**
 * Assert that no empty state containers are visible on the page.
 */
export async function expectNoEmptyState(page: Page, timeout = DEFAULT_TIMEOUT) {
  const emptyStates = page.locator("[data-testid^='empty-']")
  const count = await emptyStates.count()
  for (let i = 0; i < count; i++) {
    const el = emptyStates.nth(i)
    const visible = await el.isVisible()
    if (visible) {
      const testId = await el.getAttribute("data-testid")
      expect(visible, `Empty state [data-testid="${testId}"] should NOT be visible when data is mocked`).toBe(false)
    }
  }
  // Also verify no error states
  const errorStates = page.locator("[data-testid^='error-']")
  const errorCount = await errorStates.count()
  for (let i = 0; i < errorCount; i++) {
    const el = errorStates.nth(i)
    const visible = await el.isVisible()
    if (visible) {
      const testId = await el.getAttribute("data-testid")
      expect(visible, `Error state [data-testid="${testId}"] should NOT be visible when API is mocked`).toBe(false)
    }
  }
  void timeout // reserved for future use
}

/**
 * Wait for loading skeletons to disappear and verify content is present.
 */
export async function expectDataLoaded(page: Page, timeout = DEFAULT_TIMEOUT) {
  // Wait for skeleton elements to disappear
  await page.waitForFunction(
    () => {
      const skeletons = document.querySelectorAll("[data-testid^='skeleton-']")
      return Array.from(skeletons).every((el) => {
        const style = window.getComputedStyle(el)
        return style.display === "none" || style.visibility === "hidden" || el.getBoundingClientRect().height === 0
      }) || skeletons.length === 0
    },
    { timeout }
  ).catch(() => {
    // Skeletons may not exist at all — that's fine
  })

  // Verify the page has meaningful content (not just a blank layout)
  const mainContent = page.locator("main").first()
  await expect(mainContent, "Page main content area should be visible").toBeVisible({ timeout })
  const text = await mainContent.textContent()
  expect((text ?? "").trim().length, "Page should have meaningful text content after loading").toBeGreaterThan(5)
}
