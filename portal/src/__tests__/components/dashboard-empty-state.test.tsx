/**
 * Tests for DashboardEmptyState component (Cluster B3 — PR Phase-2 fix plan)
 *
 * After B3: the CTA calls POST /api/v1/auth/dashboard-bridge to get a
 * ?start=<code> URL instead of hardcoding the bare bot URL.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, act } from "@testing-library/react"
import { DashboardEmptyState } from "@/components/dashboard/dashboard-empty-state"

// ---------------------------------------------------------------------------
// Mock the api module so tests don't need a real Supabase session
// ---------------------------------------------------------------------------

const mockApiPost = vi.fn()

vi.mock("@/lib/api/client", () => ({
  api: {
    get: vi.fn(),
    post: (...args: unknown[]) => mockApiPost(...args),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_TELEGRAM_URL = "https://t.me/Nikita_my_bot?start=XYZABC"

describe("DashboardEmptyState", () => {
  beforeEach(() => {
    mockApiPost.mockReset()
    // Default: API call succeeds with a bridge URL
    mockApiPost.mockResolvedValue({
      telegram_url: DEFAULT_TELEGRAM_URL,
      expires_at: new Date(Date.now() + 600_000).toISOString(),
    })
  })

  it("renders the welcome heading", () => {
    render(<DashboardEmptyState />)
    expect(screen.getByText("Welcome to Nikita's World")).toBeInTheDocument()
  })

  it("has data-testid attribute for testing", () => {
    render(<DashboardEmptyState />)
    expect(screen.getByTestId("dashboard-empty-state")).toBeInTheDocument()
  })

  it("renders the body text", () => {
    render(<DashboardEmptyState />)
    expect(
      screen.getByText(/start chatting with nikita on telegram/i)
    ).toBeInTheDocument()
  })

  it("renders telegram URL from API response (no hardcoded bare URL)", async () => {
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

  it("does NOT render hardcoded bare bot URL after API success", async () => {
    render(<DashboardEmptyState />)

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /chat on telegram/i })
      expect(link.getAttribute("href")).not.toBe("https://t.me/Nikita_my_bot")
    })
  })

  it("falls back to bare bot URL when API call fails", async () => {
    mockApiPost.mockRejectedValue(new Error("network error"))

    render(<DashboardEmptyState />)

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /chat on telegram/i })
      // Fallback uses env.TELEGRAM_BOT_USERNAME — in test it's "Nikita_my_bot"
      expect(link.getAttribute("href")).toContain("t.me/")
    })

    // The fallback URL should NOT contain ?start= since no code was generated
    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link.getAttribute("href")).not.toContain("?start=")
  })

  it("opens the Telegram link in a new tab", () => {
    render(<DashboardEmptyState />)

    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
  })

  it("calls POST /auth/dashboard-bridge on mount", async () => {
    await act(async () => {
      render(<DashboardEmptyState />)
    })

    expect(mockApiPost).toHaveBeenCalledWith(
      "/auth/dashboard-bridge",
      undefined,
      undefined,
      expect.any(AbortSignal)
    )
  })
})
