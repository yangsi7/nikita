/**
 * Spec 215 FR-6 — UA detection helpers.
 *
 * Centralized per GH #420: a single source of truth for Telegram-IAB and other
 * in-app browser detection. The IS-A interstitial uses this to render an
 * "Open in Safari" Universal Link only when the page is loaded inside a
 * Telegram in-app webview (where `verifyOtp` cookies become trapped in the
 * IAB session per Apple SFSafariViewController self-contained-session).
 */

/** Telegram in-app browser UA marker (mobile + desktop). */
const TELEGRAM_IAB_PATTERN = /Telegram[/\s]/i

/**
 * True when the UA string indicates a Telegram in-app browser (iOS or Android).
 * Used to conditionally render the "Open in Safari" Universal Link in the
 * interstitial. Returns false in non-browser environments (SSR safe).
 */
export function isTelegramIAB(ua: string | null | undefined): boolean {
  if (!ua) return false
  return TELEGRAM_IAB_PATTERN.test(ua)
}
