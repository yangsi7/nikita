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

vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => ({
  useOnboardingAPI: () => ({
    converse: converseMock,
    linkTelegram: linkTelegramMock,
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

  it("I4: conversation_complete + linkMintError → falls through to ceremony (with null linkCode)", async () => {
    mockConverseOnce({ conversation_complete: true, progress_pct: 100 })
    linkTelegramMock.mockRejectedValueOnce(new Error("boom"))
    render(<OnboardingWizard userId="u1" />)
    const input = screen.getByLabelText("chat input") as HTMLInputElement
    fireEvent.change(input, { target: { value: "finish" } })
    fireEvent.submit(input.closest("form")!)

    await waitFor(() =>
      expect(screen.getByTestId("clearance-granted-ceremony")).toBeInTheDocument()
    )
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
