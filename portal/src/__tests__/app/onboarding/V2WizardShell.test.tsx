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
const mockRefreshSession = vi.fn().mockResolvedValue({
  data: { session: { access_token: "refreshed-token-456" } },
  error: null,
})
const mockSignOut = vi.fn().mockResolvedValue({ error: null })
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession: mockGetSession, refreshSession: mockRefreshSession, signOut: mockSignOut },
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

  it("includes Authorization: Bearer <access_token> in EVERY fetch request", async () => {
    render(<V2WizardShell />)
    // Use `toHaveBeenCalled` and assert against EVERY call rather
    // than `calls[0]`. Under React StrictMode (or any future double-
    // effect render), the first call may come from a discarded
    // render cycle. Pinning to index 0 would pass even if a later
    // call dropped the header — a real regression we want the test
    // to catch.
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    for (const [, init] of fetchMock.mock.calls) {
      expect(init?.headers).toMatchObject({
        Authorization: "Bearer test-jwt-123",
        "Content-Type": "application/json",
      })
    }
  })

  it("surfaces auth-missing error rather than firing fetch when no session", async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    })
    render(<V2WizardShell />)
    // Error card shows "Something went wrong." heading (Cluster X design update)
    await waitFor(() =>
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument(),
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

describe("Phase-2 slot_kind omitted (GH #606)", () => {
  /**
   * When the server returns envelope.slot === "phase2_followup", the
   * FE must OMIT slot_kind from the POST body entirely — it maps the
   * value to `undefined`, which `JSON.stringify` strips, so the key is
   * absent on the wire (NOT sent as the literal `null`). Pydantic then
   * defaults `slot_kind: SlotKindV2 | None = None`. Sending the literal
   * string "phase2_followup" 422s because the enum excludes it; the
   * test below asserts `toBeUndefined` (not `toBeNull`) to lock the
   * key-absent contract.
   */
  beforeEach(() => {
    fetchMock.mockReset()
    mockGetSession.mockReset()
    mockGetSession.mockResolvedValue(DEFAULT_SESSION_RESULT)
    installFetchStub()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("omits slot_kind when envelope.slot === 'phase2_followup'", async () => {
    const { default: userEventSetup } = await import("@testing-library/user-event")
    // First fetch (mount): return phase2_followup envelope.
    // Second fetch (submit): return complete so the component stops.
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        component: "text_long",
        slot: "phase2_followup",
        prompt: "Tell me more about your work in Berlin?",
      }),
    })
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        component: "complete",
        next_route: "/dashboard",
      }),
    })

    const user = userEventSetup.setup()
    const { getByRole } = render(<V2WizardShell />)

    // Wait for phase2_followup prompt to render
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    // Find submit button and textarea, fill in answer
    const textarea = getByRole("textbox")
    await user.click(textarea)
    await user.type(textarea, "I work on language models all day")
    const submitBtn = getByRole("button", { name: /continue|submit|next/i })
    await user.click(submitBtn)

    // Wait for second fetch
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))

    // `undefined` is stripped by JSON.stringify, so the key must be
    // completely absent from the parsed body — NOT just different from
    // "phase2_followup". toBeUndefined covers both the original bug
    // ("phase2_followup" string) AND future regressions where a stale
    // Phase-1 slot_kind leaks into Phase-2 submissions.
    const [, secondInit] = fetchMock.mock.calls[1] as [string, RequestInit]
    const body = JSON.parse(secondInit.body as string)
    expect(body.slot_kind).toBeUndefined()
    expect(body.value).toContain("language models")
  })
})

describe("Progress bar rendering (Cluster X)", () => {
  /**
   * When the server returns an envelope with progress_pct, the wizard
   * MUST render a <Progress> component with that value. Asserts the
   * FE wire-up of the Cluster X progress bar feature.
   */
  beforeEach(() => {
    fetchMock.mockReset()
    mockGetSession.mockReset()
    mockGetSession.mockResolvedValue(DEFAULT_SESSION_RESULT)
    installFetchStub()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("renders Progress component when envelope has progress_pct", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        component: "text_short",
        slot: "display_name",
        prompt: "What should I call you?",
        progress_pct: 40,
      }),
    })
    render(<V2WizardShell />)
    // Wait for the fetch to complete and component to render
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    // Progress component should be in DOM — identified by role="progressbar"
    const progressBar = await screen.findByRole("progressbar")
    expect(progressBar).toBeInTheDocument()
  })

  it("renders Progress with value 0 when progress_pct is missing", async () => {
    // Envelope without progress_pct — should default to 0, not crash
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        component: "text_short",
        slot: "display_name",
        prompt: "What should I call you?",
        // no progress_pct field
      }),
    })
    render(<V2WizardShell />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    // Should render without throwing, progressbar present
    const progressBar = await screen.findByRole("progressbar")
    expect(progressBar).toBeInTheDocument()
  })
})

describe("JWT refresh on 401 (Cluster X)", () => {
  /**
   * On 401 response, V2WizardShell must attempt a token refresh
   * and retry the fetch once. If the retry also fails, show error UI.
   * Uses the module-level mockRefreshSession defined above.
   */

  beforeEach(() => {
    fetchMock.mockReset()
    mockGetSession.mockReset()
    mockRefreshSession.mockReset()
    mockSignOut.mockReset()
    mockSignOut.mockResolvedValue({ error: null })
    mockGetSession.mockResolvedValue(DEFAULT_SESSION_RESULT)
    mockRefreshSession.mockResolvedValue({
      data: { session: { access_token: "refreshed-token-456" } },
      error: null,
    })
    installFetchStub()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("retries with refreshed token on 401 and succeeds", async () => {
    // First call 401, second call (after refresh) succeeds
    fetchMock
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          component: "text_short",
          slot: "display_name",
          prompt: "What should I call you?",
        }),
      })
    render(<V2WizardShell />)
    // After refresh+retry, the component should render the prompt
    await waitFor(() =>
      expect(screen.queryByText(/error:/i)).not.toBeInTheDocument()
    )
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("shows error UI if retry after refresh also 401", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
    render(<V2WizardShell />)
    await waitFor(() => screen.getByText(/something went wrong/i))
  })

  it("calls signOut when refreshSession returns no token (prevents infinite loop)", async () => {
    // Scenario: refresh token expired/revoked — refreshSession returns null session.
    // Without signOut, clicking "Try again" re-runs fetchTurn which hits the same
    // refresh path → error card → infinite loop. Fix: signOut on no-new-token.
    mockRefreshSession.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    })
    fetchMock.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
    render(<V2WizardShell />)
    // Error card should appear
    await waitFor(() => screen.getByText(/something went wrong/i))
    // signOut MUST have been called to clear the stale session state
    expect(mockSignOut).toHaveBeenCalledOnce()
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
  ])("rejects %s (%s)", (input, _label) => {
    expect(isSameOriginPath(input)).toBe(false)
  })

  it.each([
    [null, "null"],
    [undefined, "undefined"],
    [42, "number"],
    [{}, "object"],
  ])("rejects non-string %s (%s)", (input, _label) => {
    expect(isSameOriginPath(input)).toBe(false)
  })
})
