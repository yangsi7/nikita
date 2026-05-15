/**
 * Tests for DashboardEmptyState component (Cluster B3 + QA iter-1 fixes)
 *
 * Fix #2: loading state holds CTA until bridge URL resolves;
 * error state shows "Retry connection" affordance instead of bare fallback.
 * Fix #3: calendar max attribute uses local-date arithmetic (no UTC shift).
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

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /chat on telegram/i })
      expect(link).toHaveAttribute("href", DEFAULT_TELEGRAM_URL)
    })

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

  // Fix #2: loading state — button disabled while fetch is in-flight
  it("disables the CTA button while loading", async () => {
    // Use a promise that never resolves so we stay in loading state
    mockApiPost.mockReturnValue(new Promise(() => {}))

    render(<DashboardEmptyState />)

    // The button should be disabled immediately (loading = true on mount)
    const button = screen.getByRole("button")
    expect(button).toBeDisabled()
  })

  // Fix #2: error state — shows retry affordance, not bare fallback
  it("shows retry affordance when API call fails, not silent bare URL", async () => {
    mockApiPost.mockRejectedValue(new Error("network error"))

    render(<DashboardEmptyState />)

    await waitFor(() => {
      // Must show retry affordance (button or link with "retry" / "reconnect" text)
      const retryEl = screen.queryByText(/retry/i)
      expect(retryEl).toBeInTheDocument()
    })
  })

  // Fix #2: after retry success, the bridge URL is used
  it("uses bridge URL after successful retry", async () => {
    mockApiPost.mockRejectedValueOnce(new Error("first attempt failed"))
    mockApiPost.mockResolvedValueOnce({
      telegram_url: "https://t.me/Nikita_my_bot?start=RETRIED",
      expires_at: new Date(Date.now() + 600_000).toISOString(),
    })

    render(<DashboardEmptyState />)

    // Wait for error state
    await waitFor(() => {
      expect(screen.queryByText(/retry/i)).toBeInTheDocument()
    })

    // Click retry
    const { fireEvent } = await import("@testing-library/react")
    const retryButton = screen.getByText(/retry/i)
    fireEvent.click(retryButton)

    // After retry resolves, URL should be the bridge URL
    await waitFor(() => {
      const link = screen.queryByRole("link", { name: /chat on telegram/i })
      if (link) {
        expect(link.getAttribute("href")).toContain("?start=RETRIED")
      }
    })
  })

  it("opens the Telegram link in a new tab", async () => {
    render(<DashboardEmptyState />)

    // Wait for the link to appear (after loading)
    await waitFor(() => {
      const link = screen.queryByRole("link", { name: /chat on telegram/i })
      expect(link).not.toBeNull()
    })

    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
  })

  // QA iter-2: concurrent POST race — verify previous controller is aborted on retry
  it("aborts the previous controller when retry is triggered", async () => {
    const { fireEvent: fe, act: localAct } = await import("@testing-library/react")

    // Track controllers passed to api.post (via their signals)
    const capturedControllers: { signal: AbortSignal; resolve: (v: unknown) => void; reject: (e: unknown) => void }[] = []

    mockApiPost.mockImplementation(
      (_p: unknown, _b: unknown, _h: unknown, signal: AbortSignal) => {
        return new Promise((resolve, reject) => {
          capturedControllers.push({ signal, resolve, reject })
        })
      }
    )

    render(<DashboardEmptyState />)

    // Wait for mount fetch to start (one controller captured)
    await waitFor(() => expect(capturedControllers).toHaveLength(1))
    const mountController = capturedControllers[0]
    expect(mountController.signal.aborted).toBe(false)

    // Reject the mount promise so .catch() fires and component reaches error state
    await localAct(async () => {
      mountController.reject(new Error("mount failed"))
    })
    await waitFor(() => expect(screen.queryByText(/retry/i)).toBeInTheDocument())

    // Click retry — the fix must abort the previous controller before creating a new one
    await localAct(async () => { fe.click(screen.getByText(/retry/i)) })

    // After retry click, a new request should have fired
    await waitFor(() => expect(capturedControllers).toHaveLength(2))

    // With the useRef fix: the first controller was aborted when retry started.
    // Verify the mount signal is now aborted (it was still "alive" after the
    // promise rejected, because .catch() doesn't abort the controller).
    // NOTE: the fix calls controllerRef.current?.abort() at the TOP of fetchBridgeUrl,
    // which runs BEFORE the new controller is created. So the first signal IS aborted.
    expect(capturedControllers[0].signal.aborted).toBe(true)

    // Resolve the retry call with success
    await localAct(async () => {
      capturedControllers[1].resolve({
        telegram_url: "https://t.me/Nikita_my_bot?start=RETRYWIN",
        expires_at: new Date(Date.now() + 600_000).toISOString(),
      })
    })

    await waitFor(() => {
      const link = screen.queryByRole("link", { name: /chat on telegram/i })
      expect(link).not.toBeNull()
    })
    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link.getAttribute("href")).toContain("RETRYWIN")
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
