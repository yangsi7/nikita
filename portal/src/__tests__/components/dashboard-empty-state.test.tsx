/**
 * Tests for DashboardEmptyState component (Cluster B3 — PR Phase-2 fix plan)
 *
 * After B3: the CTA calls POST /api/v1/auth/dashboard-bridge to get a
 * ?start=<code> URL instead of hardcoding the bare bot URL.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor, act } from "@testing-library/react"
import { DashboardEmptyState } from "@/components/dashboard/dashboard-empty-state"

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

const DEFAULT_TELEGRAM_URL = "https://t.me/Nikita_my_bot?start=XYZABC"

function makeFetchMock(response: { ok: boolean; body?: object }) {
  return vi.fn().mockResolvedValue({
    ok: response.ok,
    json: vi.fn().mockResolvedValue(
      response.ok && response.body
        ? response.body
        : { error_code: "server_error" }
    ),
  })
}

describe("DashboardEmptyState", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("renders the welcome heading", () => {
    vi.stubGlobal("fetch", makeFetchMock({ ok: false }))
    render(<DashboardEmptyState />)
    expect(screen.getByText("Welcome to Nikita's World")).toBeInTheDocument()
  })

  it("has data-testid attribute for testing", () => {
    vi.stubGlobal("fetch", makeFetchMock({ ok: false }))
    render(<DashboardEmptyState />)
    expect(screen.getByTestId("dashboard-empty-state")).toBeInTheDocument()
  })

  it("renders the body text", () => {
    vi.stubGlobal("fetch", makeFetchMock({ ok: false }))
    render(<DashboardEmptyState />)
    expect(
      screen.getByText(/start chatting with nikita on telegram/i)
    ).toBeInTheDocument()
  })

  it("renders telegram URL from API response (no hardcoded bare URL)", async () => {
    const fetchMock = makeFetchMock({
      ok: true,
      body: {
        telegram_url: DEFAULT_TELEGRAM_URL,
        expires_at: new Date(Date.now() + 600_000).toISOString(),
      },
    })
    vi.stubGlobal("fetch", fetchMock)

    render(<DashboardEmptyState />)

    // Wait for the API call to resolve and link to update
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /chat on telegram/i })
      expect(link).toHaveAttribute("href", DEFAULT_TELEGRAM_URL)
    })

    // Verify the URL contains ?start= (not just bare bot URL)
    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link.getAttribute("href")).toMatch(/\?start=[A-Z0-9]{6}$/)
  })

  it("does NOT render hardcoded bare bot URL", async () => {
    const fetchMock = makeFetchMock({
      ok: true,
      body: {
        telegram_url: DEFAULT_TELEGRAM_URL,
        expires_at: new Date(Date.now() + 600_000).toISOString(),
      },
    })
    vi.stubGlobal("fetch", fetchMock)

    render(<DashboardEmptyState />)

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /chat on telegram/i })
      expect(link.getAttribute("href")).not.toBe("https://t.me/Nikita_my_bot")
    })
  })

  it("falls back to bare bot URL when API call fails", async () => {
    const fetchMock = makeFetchMock({ ok: false })
    vi.stubGlobal("fetch", fetchMock)

    render(<DashboardEmptyState />)

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /chat on telegram/i })
      // Fallback uses env.TELEGRAM_BOT_USERNAME — in test it's "Nikita_my_bot"
      expect(link.getAttribute("href")).toContain("t.me/")
    })
  })

  it("opens the Telegram link in a new tab", async () => {
    vi.stubGlobal("fetch", makeFetchMock({ ok: false }))
    render(<DashboardEmptyState />)

    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
  })

  it("calls POST /api/v1/auth/dashboard-bridge on mount", async () => {
    const fetchMock = makeFetchMock({
      ok: true,
      body: {
        telegram_url: DEFAULT_TELEGRAM_URL,
        expires_at: new Date(Date.now() + 600_000).toISOString(),
      },
    })
    vi.stubGlobal("fetch", fetchMock)

    await act(async () => {
      render(<DashboardEmptyState />)
    })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/dashboard-bridge"),
      expect.objectContaining({ method: "POST" })
    )
  })
})
