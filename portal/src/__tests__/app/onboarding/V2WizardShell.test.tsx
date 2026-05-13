/**
 * GH #594 — V2WizardShell must attach Authorization: Bearer <access_token>
 * to every POST /api/v1/onboarding/answer call. Walk Final (2026-05-13)
 * caught the missing-header bug producing a 401 boundary on mount.
 *
 * RED (master): fetch mock observes no Authorization header.
 * GREEN: V2WizardShell pulls session via createBrowserClient and injects
 *        `Authorization: Bearer <token>` on every fetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"

// Supabase client mock — session present, access_token === "test-jwt-123"
const mockGetSession = vi.fn().mockResolvedValue({
  data: { session: { access_token: "test-jwt-123" } },
  error: null,
})
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession: mockGetSession },
  }),
}))

// fetch mock — first turn returns a text_short envelope so the component
// finishes loading and the assertions run against the captured headers.
const fetchMock = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({
    component: "text_short",
    slot: "display_name",
    prompt: "What name should I use?",
  }),
})
vi.stubGlobal("fetch", fetchMock)

import { V2WizardShell } from "@/app/onboarding/V2WizardShell"

describe("V2WizardShell auth header (GH #594)", () => {
  beforeEach(() => {
    fetchMock.mockClear()
    mockGetSession.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("includes Authorization: Bearer <access_token> in fetch request", async () => {
    render(<V2WizardShell />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [, init] = fetchMock.mock.calls[0]
    expect(init?.headers).toMatchObject({
      Authorization: "Bearer test-jwt-123",
      "Content-Type": "application/json",
    })
  })

  it("surfaces auth-missing error rather than firing fetch when no session", async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    })
    render(<V2WizardShell />)
    await waitFor(() =>
      expect(screen.getByText(/error:/i)).toBeInTheDocument(),
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
