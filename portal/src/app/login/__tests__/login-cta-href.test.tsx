import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn(), replace: vi.fn() }),
}))

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import LoginPage from "../page-client"

/**
 * Spec 217-1 FR-1 / AC-1.3 — `/login` (post-Spec 216-G TG-first surface)
 * "Open Telegram" CTA must carry `?start=welcome` payload.
 *
 * Single CTA only — the page is shown on sign-out and on /auth/confirm
 * failure (the only branches per CLAUDE.md). No authenticated branch.
 */
describe("Spec 217-1 FR-1 — /login Telegram CTA carries ?start=welcome", () => {
  it("login Telegram CTA URL.searchParams.start === 'welcome'", () => {
    render(<LoginPage />)
    const cta = screen.getByTestId("login-telegram-cta")
    const href = cta.getAttribute("href")!
    const url = new URL(href)
    expect(url.host).toBe("t.me")
    expect(url.pathname).toBe("/Nikita_my_bot")
    expect(url.searchParams.get("start")).toBe("welcome")
  })
})
