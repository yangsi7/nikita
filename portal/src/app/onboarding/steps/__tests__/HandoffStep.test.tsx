import { describe, it, expect, vi, afterEach, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"

// GH #321 REQ-1: HandoffStep calls `useOnboardingAPI().linkTelegram()` on
// mount to mint a single-use 6-char deep-link token. Mock the hook here so
// the tests stay isolated from the network.
vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => ({
  useOnboardingAPI: vi.fn(),
}))

import { HandoffStep } from "@/app/onboarding/steps/HandoffStep"
import { WIZARD_COPY, TELEGRAM_URL } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"
import { useOnboardingAPI } from "@/app/onboarding/hooks/use-onboarding-api"

const mockedUseOnboardingAPI = useOnboardingAPI as unknown as ReturnType<
  typeof vi.fn
>

// Spec 214 PR 214-B — T208 (RED)
// Tests:
//   AC-NR4.1: QR renders on desktop only (delegated to QRHandoff).
//   AC-NR5.1: voice path → pulsing ring + "Nikita is calling you now."
//   AC-NR5.2: on degraded/failed → ring hides, Telegram CTA + QR display.
//   AC-NR5.3: Telegram deeplink always visible as secondary option.
//   AC-NR5.4: data-testid="voice-ring-animation" + "voice-fallback-telegram".
//   AC-NR5.5: role="status" aria-live="polite" announces fallback transition.

function mockMatchMedia(desktopMatches: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: desktopMatches && /min-width/.test(query),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

const voicePathValues: WizardFormValues = {
  location_city: "Berlin",
  social_scene: "techno",
  drug_tolerance: 3,
  life_stage: "tech",
  interest: null,
  name: null,
  age: null,
  occupation: null,
  phone: "+12025550100",
  chosen_option_id: "id-a",
  cache_key: "k1",
}

const textPathValues: WizardFormValues = {
  ...voicePathValues,
  phone: null,
}

// Default: linkTelegram resolves with a fixed code so existing tests that
// don't care about the binding still exercise the happy path.
beforeEach(() => {
  mockedUseOnboardingAPI.mockReturnValue({
    linkTelegram: vi.fn().mockResolvedValue({
      code: "ABC123",
      expires_at: "2026-04-17T20:00:00Z",
      instructions: "Send /start ABC123 to @Nikita_my_bot on Telegram.",
    }),
    // The other hook methods aren't used by HandoffStep but return no-ops
    // so a broader smoke test won't blow up.
    previewBackstory: vi.fn(),
    submitProfile: vi.fn(),
    patchProfile: vi.fn(),
    selectBackstory: vi.fn(),
  })
})

describe("HandoffStep (Step 11) — text path", () => {
  afterEach(() => vi.resetAllMocks())

  it("renders with data-testid='wizard-step-11' (AC-1.5)", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )
    expect(screen.getByTestId("wizard-step-11")).toBeInTheDocument()
  })

  it("shows the Telegram deeplink CTA with the canonical copy (AC-NR5.3)", async () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )
    // Wait for linkTelegram() to resolve and the CTA href to arm.
    await waitFor(() => {
      const cta = screen.getByRole("link", { name: WIZARD_COPY.handoff.telegramCTA })
      expect(cta).toBeInTheDocument()
      // GH #321 REQ-1: href includes ?start=<code>, not bare TELEGRAM_URL.
      // Starts with the canonical URL, carries a 6-char uppercase alnum code.
      expect(cta.getAttribute("href")).toMatch(
        new RegExp(`^${TELEGRAM_URL}\\?start=[A-Z0-9]{6}$`)
      )
    })
  })

  it("does NOT render the voice ring on the text path", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )
    expect(screen.queryByTestId("voice-ring-animation")).toBeNull()
  })
})

describe("HandoffStep (Step 11) — voice path + ring", () => {
  afterEach(() => vi.resetAllMocks())

  it("renders the voice ring animation with data-testid='voice-ring-animation' (AC-NR5.4)", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={voicePathValues}
        onAdvance={vi.fn()}
        voiceCallState="ringing"
      />
    )
    expect(screen.getByTestId("voice-ring-animation")).toBeInTheDocument()
    expect(screen.getByText(WIZARD_COPY.handoff.voiceHeadline)).toBeInTheDocument()
  })

  it("shows Telegram CTA as a secondary option below the ring (AC-NR5.3)", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={voicePathValues}
        onAdvance={vi.fn()}
        voiceCallState="ringing"
      />
    )
    expect(
      screen.getByRole("link", { name: WIZARD_COPY.handoff.telegramCTA })
    ).toBeInTheDocument()
  })

  it("always mounts a role='status' aria-live region (AC-NR5.5)", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={voicePathValues}
        onAdvance={vi.fn()}
        voiceCallState="ringing"
      />
    )
    const status = screen.getByRole("status")
    expect(status).toHaveAttribute("aria-live", "polite")
  })
})

describe("HandoffStep (Step 11) — voice fallback (AC-NR5.2)", () => {
  afterEach(() => vi.resetAllMocks())

  it("hides the ring and shows the Telegram fallback when voiceCallState='unavailable'", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={voicePathValues}
        onAdvance={vi.fn()}
        voiceCallState="unavailable"
      />
    )
    expect(screen.queryByTestId("voice-ring-animation")).toBeNull()
    expect(screen.getByTestId("voice-fallback-telegram")).toBeInTheDocument()
    expect(
      screen.getByText(WIZARD_COPY.handoff.fallbackHeadline)
    ).toBeInTheDocument()
  })

  it("announces the fallback transition via role='status' (AC-NR5.5)", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={voicePathValues}
        onAdvance={vi.fn()}
        voiceCallState="unavailable"
      />
    )
    const status = screen.getByRole("status")
    expect(status.textContent ?? "").toMatch(/Voice unavailable/i)
  })
})

describe("HandoffStep (Step 11) — QRHandoff gating (AC-NR4.1)", () => {
  afterEach(() => vi.resetAllMocks())

  it("renders the QR code on desktop viewport", () => {
    mockMatchMedia(true)
    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )
    // Figure rendered by QRHandoff
    expect(screen.getByRole("figure")).toBeInTheDocument()
  })

  it("does NOT render the QR on mobile viewport", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )
    expect(screen.queryByRole("figure")).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// GH #321 REQ-1 — HandoffStep mints + consumes a deep-link binding token
// ---------------------------------------------------------------------------
describe("HandoffStep (Step 11) — Telegram binding token (GH #321 REQ-1)", () => {
  afterEach(() => vi.resetAllMocks())

  it("calls linkTelegram() on mount (AC-11b.1)", async () => {
    mockMatchMedia(false)
    const linkTelegramMock = vi.fn().mockResolvedValue({
      code: "DEF456",
      expires_at: "2026-04-17T20:10:00Z",
      instructions: "",
    })
    mockedUseOnboardingAPI.mockReturnValue({
      linkTelegram: linkTelegramMock,
      previewBackstory: vi.fn(),
      submitProfile: vi.fn(),
      patchProfile: vi.fn(),
      selectBackstory: vi.fn(),
    })

    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )

    await waitFor(() => {
      expect(linkTelegramMock).toHaveBeenCalledTimes(1)
    })
  })

  it("arms CTA href as t.me/Nikita_my_bot?start=<code> after linkTelegram resolves (AC-11b.2)", async () => {
    mockMatchMedia(false)
    mockedUseOnboardingAPI.mockReturnValue({
      linkTelegram: vi.fn().mockResolvedValue({
        code: "GHIJKL",
        expires_at: "2026-04-17T20:10:00Z",
        instructions: "",
      }),
      previewBackstory: vi.fn(),
      submitProfile: vi.fn(),
      patchProfile: vi.fn(),
      selectBackstory: vi.fn(),
    })

    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )

    await waitFor(() => {
      const cta = screen.getByRole("link", { name: WIZARD_COPY.handoff.telegramCTA })
      expect(cta.getAttribute("href")).toBe(`${TELEGRAM_URL}?start=GHIJKL`)
    })
  })

  it("does NOT fall back to bare t.me URL on linkTelegram failure (per brief Q-3)", async () => {
    // Brief Q-3: bare-URL fallback reproduces the #321 bug class. The CTA
    // MUST NOT render with a bare href; an error state (retry button or
    // disabled CTA) is the correct degraded path.
    mockMatchMedia(false)
    mockedUseOnboardingAPI.mockReturnValue({
      linkTelegram: vi.fn().mockRejectedValue(new Error("server 500")),
      previewBackstory: vi.fn(),
      submitProfile: vi.fn(),
      patchProfile: vi.fn(),
      selectBackstory: vi.fn(),
    })

    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )

    // Wait for the rejection to settle.
    await waitFor(() => {
      const ctas = screen.queryAllByRole("link", {
        name: WIZARD_COPY.handoff.telegramCTA,
      })
      // After failure: no armed CTA link with a bare URL. Either no link
      // renders, or the CTA exists but with no ?start= param (the impl
      // may choose to render a disabled button instead). Either is
      // acceptable. What MUST NOT happen: an armed href === TELEGRAM_URL
      // (bare), which reproduces the #321 orphan-row bug.
      for (const cta of ctas) {
        const href = cta.getAttribute("href") ?? ""
        expect(href).not.toBe(TELEGRAM_URL)
      }
    })
  })
})
