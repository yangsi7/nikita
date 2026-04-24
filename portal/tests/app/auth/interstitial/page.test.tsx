/**
 * Spec 215 PR-F2a / Tasks T022 — IS-A interstitial page tests.
 *
 * Behavior under test (FR-6, FR-6a, Testing H4):
 * - Always renders the interstitial (no UA-conditional skip).
 * - Primary "Continue to Nikita" button always renders.
 * - "Open in Safari" Universal Link renders ONLY when UA matches Telegram-IAB.
 * - ARIA contract: role="main", aria-labelledby, aria-describedby.
 * - Primary button navigates to `?next` when clicked (via router.push).
 * - Same-origin guard: rejects external `next` values, falls back to /dashboard.
 *
 * Mapped: AC-6.4, AC-6.5, FR-6a, Testing H4.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import InterstitialClient from "@/app/auth/interstitial/InterstitialClient"

// next/navigation mock — capture router.push calls
const mockPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(mockSearchParams.value),
}))

const mockSearchParams = { value: "next=/dashboard" }

const ORIGINAL_UA = typeof navigator !== "undefined" ? navigator.userAgent : ""

function setUserAgent(ua: string) {
  Object.defineProperty(navigator, "userAgent", {
    configurable: true,
    get: () => ua,
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  mockSearchParams.value = "next=/dashboard"
  setUserAgent("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1")
})

afterEach(() => {
  setUserAgent(ORIGINAL_UA)
})

describe("InterstitialClient — primary button + ARIA (AC-6.4, FR-6a)", () => {
  it("renders 'Continue to Nikita' primary button with describedby", () => {
    render(<InterstitialClient />)
    const btn = screen.getByRole("button", { name: /continue to nikita/i })
    expect(btn).toBeInTheDocument()
    expect(btn).toHaveAttribute("aria-describedby", "interstitial-subtitle")
  })

  it("root has role='main' and card has aria-labelledby='interstitial-title'", () => {
    render(<InterstitialClient />)
    expect(screen.getByRole("main")).toBeInTheDocument()
    const title = screen.getByText(/cleared\. enter the portal\./i)
    expect(title).toHaveAttribute("id", "interstitial-title")
  })

  it("renders Nikita-voiced title and subtitle copy", () => {
    render(<InterstitialClient />)
    expect(screen.getByText(/cleared\. enter the portal\./i)).toBeInTheDocument()
    expect(screen.getByText(/tap to enter your portal\./i)).toBeInTheDocument()
  })

  it("primary button click → router.push(next)", () => {
    render(<InterstitialClient />)
    fireEvent.click(screen.getByRole("button", { name: /continue to nikita/i }))
    expect(mockPush).toHaveBeenCalledWith("/dashboard")
  })

  it("rejects external next, falls back to /dashboard on click", () => {
    mockSearchParams.value = "next=https://evil.com"
    render(<InterstitialClient />)
    fireEvent.click(screen.getByRole("button", { name: /continue to nikita/i }))
    expect(mockPush).toHaveBeenCalledWith("/dashboard")
  })

  it("rejects protocol-relative next, falls back to /dashboard", () => {
    mockSearchParams.value = "next=//evil.com"
    render(<InterstitialClient />)
    fireEvent.click(screen.getByRole("button", { name: /continue to nikita/i }))
    expect(mockPush).toHaveBeenCalledWith("/dashboard")
  })
})

describe("InterstitialClient — IAB detection (AC-6.5, Testing H4)", () => {
  it("iOS Safari UA → does NOT render 'Open in Safari' link", () => {
    setUserAgent(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    )
    render(<InterstitialClient />)
    expect(screen.queryByRole("link", { name: /open in safari/i })).toBeNull()
  })

  it("Telegram in-app browser UA → renders 'Open in Safari' link", () => {
    setUserAgent(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Telegram/10.4",
    )
    render(<InterstitialClient />)
    // Match by aria-label since `Button asChild + variant="link"` may interfere
    // with testing-library's accessible-name resolution for some configurations.
    const link = screen.getByLabelText("Open this page in Safari")
    expect(link).toBeInTheDocument()
    expect(link.tagName.toLowerCase()).toBe("a")
    expect(link).toHaveAttribute("href")
  })
})
