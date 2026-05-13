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

import { V2WizardShell, isSameOriginPath } from "@/app/onboarding/V2WizardShell"

describe("V2WizardShell auth header (GH #594)", () => {
  beforeEach(() => {
    fetchMock.mockClear()
    mockGetSession.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    // `vi.stubGlobal` is module-level and persists across files in the
    // same Vitest worker; `restoreAllMocks` does NOT unstub it. Explicit
    // teardown prevents the stub from leaking into unrelated test files
    // that rely on the real `fetch`.
    vi.unstubAllGlobals()
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

describe("isSameOriginPath (CompleteRedirect open-redirect guard)", () => {
  it.each([
    ["/dashboard", true],
    ["/onboarding/v2", true],
    ["/", true],
  ])("accepts same-origin path %s", (input, expected) => {
    expect(isSameOriginPath(input)).toBe(expected)
  })

  it.each([
    ["//evil.com", "protocol-relative"],
    ["/\\evil.com", "backslash-host-delimiter"],
    ["https://evil.com/x", "absolute-url"],
    ["javascript:alert(1)", "javascript-scheme"],
    ["data:text/html,<script>1</script>", "data-uri"],
    ["evil.com/path", "no-leading-slash"],
    ["", "empty-string"],
  ])("rejects %s (%s)", (input) => {
    expect(isSameOriginPath(input)).toBe(false)
  })

  it.each([
    [null, "null"],
    [undefined, "undefined"],
    [42, "number"],
    [{}, "object"],
  ])("rejects non-string %s (%s)", (input) => {
    expect(isSameOriginPath(input)).toBe(false)
  })
})
