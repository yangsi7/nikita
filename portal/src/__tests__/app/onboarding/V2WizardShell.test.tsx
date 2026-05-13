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

// Defaults reinstalled in beforeEach via mockReset (clears queued
// `mockResolvedValueOnce` overrides as well as call history; mockClear
// only zeros call counts).
const DEFAULT_SESSION_RESULT = {
  data: { session: { access_token: "test-jwt-123" } },
  error: null,
}
const DEFAULT_FETCH_RESULT = {
  ok: true,
  json: async () => ({
    component: "text_short",
    slot: "display_name",
    prompt: "What name should I use?",
  }),
}

// Re-stub fetch on every test — `unstubAllGlobals()` in afterEach
// removes the module-level stub between tests, so each test installs
// it fresh. This keeps test isolation tight (no stub leak across
// files) without giving up the stub inside the file.
function installFetchStub() {
  vi.stubGlobal("fetch", fetchMock)
}

describe("V2WizardShell auth header (GH #594)", () => {
  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockResolvedValue(DEFAULT_FETCH_RESULT)
    mockGetSession.mockReset()
    mockGetSession.mockResolvedValue(DEFAULT_SESSION_RESULT)
    installFetchStub()
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
    // `toHaveBeenCalled` (not `toHaveBeenCalledTimes(1)`) is the
    // intent-bearing assertion here: every call must carry the Bearer
    // token. Counting calls would couple the test to render-cycle
    // implementation details (e.g. a future StrictMode wrap that
    // double-invokes effects).
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
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

describe("CompleteRedirect open-redirect integration (security)", () => {
  // Integration test: regardless of whether `isSameOriginPath` flips
  // inverted in a future diff, the production call-site at
  // V2WizardShell.tsx:CompleteRedirect must NEVER navigate to an
  // attacker-controlled target. Spy on window.location to assert.

  const origLocation = window.location
  let assignedHref = ""

  beforeEach(() => {
    // Re-install fetch/session defaults — this describe block does
    // not inherit beforeEach from the sibling auth-header describe.
    fetchMock.mockReset()
    fetchMock.mockResolvedValue(DEFAULT_FETCH_RESULT)
    mockGetSession.mockReset()
    mockGetSession.mockResolvedValue(DEFAULT_SESSION_RESULT)
    installFetchStub()
    assignedHref = ""
    // JSDOM `window.location` is read-only; redefine as a plain object
    // with a setter that records the assignment.
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: {
        get href() {
          return assignedHref
        },
        set href(v: string) {
          assignedHref = v
        },
      },
    })
  })

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: origLocation,
    })
  })

  it("rejects an attacker-controlled next_route and lands on /dashboard", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        component: "complete",
        next_route: "//evil.com/steal",
      }),
    })
    render(<V2WizardShell />)
    await waitFor(() => expect(assignedHref).toBe("/dashboard"))
    expect(assignedHref).not.toContain("evil.com")
  })

  it("honors a safe same-origin next_route", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        component: "complete",
        next_route: "/dashboard/insights",
      }),
    })
    render(<V2WizardShell />)
    await waitFor(() => expect(assignedHref).toBe("/dashboard/insights"))
  })
})

describe("isSameOriginPath (CompleteRedirect open-redirect guard)", () => {
  // Pure-function tests; no fetch needed but the module-level stub
  // may still be active from prior tests' beforeEach. Harmless.
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
    ["/\tevil.com", "tab-host-delimiter"],
    ["/\nevil.com", "newline-host-delimiter"],
    ["/ evil.com", "space-host-delimiter"],
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
