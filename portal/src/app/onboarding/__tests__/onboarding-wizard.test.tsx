/**
 * Spec 214 T3.9 — OnboardingWizard rewrite tests.
 *
 * ACs:
 *   - AC-T3.9.1: on conversation_complete=true, ClearanceGrantedCeremony mounts
 *   - AC-T3.9.2: NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD=true routes to legacy
 *   - AC-T3.9.4: POST /portal/link-telegram fires BEFORE ceremony mounts
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const converseMock = vi.fn()
const linkTelegramMock = vi.fn()
const getConversationMock = vi.fn()

vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => ({
  useOnboardingAPI: () => ({
    converse: converseMock,
    linkTelegram: linkTelegramMock,
    getConversation: getConversationMock,
    previewBackstory: vi.fn(),
    submitProfile: vi.fn(),
    patchProfile: vi.fn(),
    selectBackstory: vi.fn(),
  }),
}))

// Mock virtuoso to just render children eagerly.
vi.mock("react-virtuoso", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Virtuoso: ({ data, itemContent }: any) => (
    <div data-testid="virtuoso-mock">
      {data.map((t: unknown, i: number) => (
        <div key={i}>{itemContent(i, t)}</div>
      ))}
    </div>
  ),
}))

// Mock DossierStamp for the ceremony stub.
vi.mock("@/app/onboarding/components/DossierStamp", () => ({
  DossierStamp: () => <div data-testid="dossier-stamp" />,
}))

// Mock LegacyOnboardingWizard so AC-T3.9.2 test doesn't load the entire
// legacy tree (which would pull many more mocks in).
vi.mock("@/app/onboarding/onboarding-wizard-legacy", () => ({
  LegacyOnboardingWizard: () => <div data-testid="legacy-wizard" />,
}))

import { OnboardingWizard } from "../onboarding-wizard"

function mockConverseOnce(responseOverrides: Record<string, unknown> = {}) {
  converseMock.mockResolvedValueOnce({
    nikita_reply: "zurich. nice.",
    extracted_fields: { location_city: "Zurich" },
    confirmation_required: false,
    next_prompt_type: "chips",
    next_prompt_options: ["techno", "jazz"],
    progress_pct: 40,
    conversation_complete: false,
    source: "llm",
    latency_ms: 100,
    ...responseOverrides,
  })
}

describe("OnboardingWizard — AC-T3.9.1 completion mounts ceremony", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    converseMock.mockReset()
    linkTelegramMock.mockReset()
    getConversationMock.mockReset()
    // Default: empty history so wizard shows hardcoded opener.
    getConversationMock.mockResolvedValue({ conversation: [], progress_pct: 0, elided_extracted: {} })
    delete process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD
  })

  it("renders chat wizard opener + input on mount", () => {
    render(<OnboardingWizard userId="u1" />)
    expect(screen.getByTestId("chat-log")).toBeInTheDocument()
    expect(screen.getByTestId("progress-header")).toBeInTheDocument()
    // Free-text input is the default prompt.
    expect(screen.getByLabelText("chat input")).toBeInTheDocument()
  })

  it("AC-T3.9.1: on conversation_complete → ClearanceGrantedCeremony paints", async () => {
    mockConverseOnce({ conversation_complete: true, progress_pct: 100 })
    linkTelegramMock.mockResolvedValueOnce({
      code: "ABC123",
      expires_at: "2026-04-20T00:00:00Z",
    })
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "finish" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() =>
      expect(screen.getByTestId("clearance-granted-ceremony")).toBeInTheDocument()
    )
  })

  it("AC-T3.9.4: linkTelegram fires BEFORE ceremony mounts (ordering guarantee)", async () => {
    mockConverseOnce({ conversation_complete: true, progress_pct: 100 })
    let linkResolvedAt = 0
    let ceremonyMountedAt = 0
    linkTelegramMock.mockImplementationOnce(async () => {
      linkResolvedAt = Date.now()
      return { code: "XYZ789", expires_at: "2026-04-20T00:00:00Z" }
    })
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "finish" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByTestId("clearance-granted-ceremony")).toBeInTheDocument()
      ceremonyMountedAt = Date.now()
    })
    // linkTelegram was called; ceremony only paints AFTER resolution.
    expect(linkTelegramMock).toHaveBeenCalledTimes(1)
    expect(linkResolvedAt).toBeGreaterThan(0)
    expect(ceremonyMountedAt).toBeGreaterThanOrEqual(linkResolvedAt)
    // CTA href includes the minted code (ensures state.linkCode was set).
    const cta = screen.getByTestId("ceremony-cta") as HTMLAnchorElement
    expect(cta.href).toContain("start=XYZ789")
  })
})

describe("OnboardingWizard — AC-T3.9.2 feature flag routes to legacy", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getConversationMock.mockResolvedValue({ conversation: [], progress_pct: 0, elided_extracted: {} })
  })
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD
  })

  it("flag=true renders LegacyOnboardingWizard (not chat)", () => {
    process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD = "true"
    render(<OnboardingWizard userId="u1" />)
    expect(screen.getByTestId("legacy-wizard")).toBeInTheDocument()
    expect(screen.queryByTestId("chat-log")).toBeNull()
  })

  it("flag unset defaults to chat wizard (not legacy)", () => {
    render(<OnboardingWizard userId="u1" />)
    expect(screen.queryByTestId("legacy-wizard")).toBeNull()
    expect(screen.getByTestId("chat-log")).toBeInTheDocument()
  })
})

describe("OnboardingWizard — PR #363 QA iter-1 fixes", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    converseMock.mockReset()
    linkTelegramMock.mockReset()
    getConversationMock.mockReset()
    getConversationMock.mockResolvedValue({ conversation: [], progress_pct: 0, elided_extracted: {} })
    delete process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD
  })

  it("I3: on 429, preserves the prior control (chips/options) instead of demoting to text", async () => {
    // First turn: server responds with a `chips` control surfaced inline.
    mockConverseOnce({
      nikita_reply: "pick one.",
      next_prompt_type: "chips",
      next_prompt_options: ["techno", "jazz"],
    })
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "zurich" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByTestId("chips-control")).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "techno" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "jazz" })).toBeInTheDocument()
    })

    // Second turn: 429 fired by next submit. Fallback must preserve the
    // chips control; the wizard SHOULD NOT demote the input to free text.
    const rateLimitErr = {
      status: 429,
      detail: { nikita_reply: "easy, tiger. give me a sec." },
      name: "Error",
    }
    converseMock.mockRejectedValueOnce(rateLimitErr)
    fireEvent.click(screen.getByRole("button", { name: "techno" }))

    await waitFor(() => {
      expect(
        screen.getByText("easy, tiger. give me a sec.")
      ).toBeInTheDocument()
    })
    // Chips should STILL be the active control after the 429.
    expect(screen.getByTestId("chips-control")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "techno" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "jazz" })).toBeInTheDocument()
  })

  it("I4: conversation_complete + linkCode unresolved → neutral loading interstitial (not ceremony)", async () => {
    mockConverseOnce({ conversation_complete: true, progress_pct: 100 })
    // linkTelegram pending forever for this test (never resolves).
    linkTelegramMock.mockImplementationOnce(
      () => new Promise(() => {})
    )
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "finish" } })
    fireEvent.submit(input.closest("form")!)

    // While the link code is being minted, we should see the loading state
    // (NOT the ceremony) and NOT the "link token missing" error.
    await waitFor(() =>
      expect(screen.getByTestId("ceremony-loading")).toBeInTheDocument()
    )
    expect(screen.queryByTestId("clearance-granted-ceremony")).toBeNull()
    expect(screen.queryByText(/link mint failed/i)).toBeNull()
  })

  it("I4: conversation_complete + linkMintError → shows link-mint error state (NOT ceremony)", async () => {
    // Spec 214 T4.1 / AC-T4.1.3 (FR-11e): the ceremony hard-throws on a
    // null linkCode. The wizard MUST detect the link-mint failure and
    // surface a recoverable error UI instead of mounting the ceremony
    // (which would otherwise produce a silent-strand CTA pointing at
    // `t.me/...?start=`). PR-3 had a stub that allowed this fallthrough;
    // PR-4 hardens both halves.
    mockConverseOnce({ conversation_complete: true, progress_pct: 100 })
    linkTelegramMock.mockRejectedValueOnce(new Error("boom"))
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "finish" } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() =>
      expect(screen.getByTestId("ceremony-link-error")).toBeInTheDocument()
    )
    // Ceremony MUST NOT mount with a null linkCode.
    expect(screen.queryByTestId("clearance-granted-ceremony")).toBeNull()
  })

  it("N1: AbortError (timeout) from converse → reducer timeout action, in-character fallback bubble", async () => {
    const timeoutErr = Object.assign(new Error("timeout"), { name: "TimeoutError" })
    converseMock.mockRejectedValueOnce(timeoutErr)
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "zurich" } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() =>
      expect(
        screen.getByText("i lost the signal for a sec. try again.")
      ).toBeInTheDocument()
    )
  })

  it("N2: converse receives the full conversation_history including the user turn just submitted", async () => {
    mockConverseOnce({ nikita_reply: "ack" })
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "zurich" } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() => expect(converseMock).toHaveBeenCalledTimes(1))
    const firstCall = converseMock.mock.calls[0][0]
    const history = firstCall.conversation_history as Array<{ role: string; content: string }>
    // Opener (nikita) + the user turn we just sent should both appear.
    expect(history.at(-1)?.role).toBe("user")
    expect(history.at(-1)?.content).toBe("zurich")
  })

  it("GH #376: conversation_history Turn rows must NOT contain client-only fields (turn_id, superseded)", async () => {
    // Backend Turn model in nikita/agents/onboarding/converse_contracts.py:24
    // sets ConfigDict(extra='forbid'). Allowed keys: role, content, extracted,
    // timestamp, source. Forwarding client-only fields (turn_id, superseded)
    // triggers HTTP 422 — exactly the Walk O 2026-04-21 finding.
    mockConverseOnce({ nikita_reply: "ack" })
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "zurich" } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() => expect(converseMock).toHaveBeenCalledTimes(1))
    const firstCall = converseMock.mock.calls[0][0]
    const history = firstCall.conversation_history as Array<Record<string, unknown>>
    // Mirrors the backend Turn allow-list at
    // nikita/agents/onboarding/converse_contracts.py:23-35
    // (class def :23, ConfigDict extra='forbid' :27). If the backend adds
    // a new allowed field, update BOTH this set AND the toWireTurn
    // serializer in portal/src/app/onboarding/hooks/use-onboarding-api.ts.
    const allowedTurnKeys = new Set([
      "role",
      "content",
      "extracted",
      "timestamp",
      "source",
    ])
    for (const turn of history) {
      const extraKeys = Object.keys(turn).filter(
        (k) => !allowedTurnKeys.has(k)
      )
      expect(extraKeys).toEqual([])
    }
  })
})

describe("OnboardingWizard — AC-T3.9.3 legacy files live under steps/legacy/", () => {
  it("steps/legacy contains the 6 retired step files", async () => {
    const { readdirSync } = await import("node:fs")
    const { join } = await import("node:path")
    const dir = join(__dirname, "..", "steps", "legacy")
    const files = readdirSync(dir).filter((f) => f.endsWith(".tsx"))
    expect(files.sort()).toEqual(
      [
        "BackstoryReveal.tsx",
        "DarknessStep.tsx",
        "IdentityStep.tsx",
        "LocationStep.tsx",
        "PhoneStep.tsx",
        "SceneStep.tsx",
      ].sort()
    )
  })
})

describe("OnboardingWizard — GH #385 conversation hydration on mount", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    converseMock.mockReset()
    linkTelegramMock.mockReset()
    getConversationMock.mockReset()
    delete process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD
  })

  it("calls getConversation on mount to check for existing history", async () => {
    getConversationMock.mockResolvedValueOnce({
      conversation: [],
      progress_pct: 0,
      elided_extracted: {},
    })
    render(<OnboardingWizard userId="u1" />)
    await waitFor(() => {
      expect(getConversationMock).toHaveBeenCalledTimes(1)
    })
  })

  it("renders prior turns from backend when getConversation returns non-empty history", async () => {
    getConversationMock.mockResolvedValueOnce({
      conversation: [
        {
          role: "nikita",
          content: "hey. building your file...",
          timestamp: "2026-04-21T10:00:00Z",
          source: "llm",
        },
        {
          role: "user",
          content: "zurich is home",
          timestamp: "2026-04-21T10:01:00Z",
        },
        {
          role: "nikita",
          content: "tell me more about zurich.",
          timestamp: "2026-04-21T10:02:00Z",
          source: "llm",
        },
      ],
      progress_pct: 20,
      elided_extracted: {},
    })
    render(<OnboardingWizard userId="u1" />)
    await waitFor(() => {
      // ChatShell renders each turn as visible + sr-only spans; use getAllByText.
      expect(screen.getAllByText("zurich is home")[0]).toBeInTheDocument()
      expect(screen.getAllByText("tell me more about zurich.")[0]).toBeInTheDocument()
    })
  })

  it("falls back to hardcoded greeting when getConversation returns empty conversation", async () => {
    getConversationMock.mockResolvedValueOnce({
      conversation: [],
      progress_pct: 0,
      elided_extracted: {},
    })
    render(<OnboardingWizard userId="u1" />)
    await waitFor(() => {
      expect(screen.getByText(/hey\. building your file/i)).toBeInTheDocument()
    })
  })
})
