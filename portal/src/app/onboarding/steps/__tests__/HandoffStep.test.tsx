import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"

import { HandoffStep } from "@/app/onboarding/steps/HandoffStep"
import { WIZARD_COPY, TELEGRAM_URL } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

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

  it("shows the Telegram deeplink CTA with the canonical copy (AC-NR5.3)", () => {
    mockMatchMedia(false)
    render(
      <HandoffStep
        values={textPathValues}
        onAdvance={vi.fn()}
        voiceCallState="idle"
      />
    )
    const cta = screen.getByRole("link", { name: WIZARD_COPY.handoff.telegramCTA })
    expect(cta).toBeInTheDocument()
    expect(cta).toHaveAttribute("href", TELEGRAM_URL)
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
