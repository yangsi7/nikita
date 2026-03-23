/**
 * Console error collection and assertion helpers for Playwright E2E tests.
 *
 * Usage:
 *   const errors = collectConsoleErrors(page)
 *   // ... navigate and interact ...
 *   assertNoConsoleErrors(errors)
 */

import type { Page, ConsoleMessage } from "@playwright/test"

/**
 * Start collecting console errors from a Playwright page.
 * Call this BEFORE navigating to any page.
 * Returns a mutable array that accumulates errors as they occur.
 */
export function collectConsoleErrors(page: Page): ConsoleMessage[] {
  const errors: ConsoleMessage[] = []
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg)
    }
  })
  return errors
}

/**
 * Assert that no unexpected console errors were logged.
 * Optionally pass an allowList of substrings to ignore known/benign errors.
 */
export function assertNoConsoleErrors(errors: ConsoleMessage[], allowList: string[] = []) {
  const filtered = errors.filter(
    (e) => !allowList.some((pattern) => e.text().includes(pattern))
  )
  if (filtered.length > 0) {
    throw new Error(
      `Found ${filtered.length} console error(s):\n${filtered.map((e) => `  - ${e.text()}`).join("\n")}`
    )
  }
}
