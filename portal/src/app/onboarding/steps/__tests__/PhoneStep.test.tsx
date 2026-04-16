import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

import { PhoneStep } from "@/app/onboarding/steps/PhoneStep"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T206 (RED)
// Tests:
//   AC-NR3.1: unsupported dial code → inline Nikita-voiced message + auto-
//              select Telegram path, no network call.
//   AC-NR3.2: E.164 validation runs before country-support check.
//   AC-NR3.3: data-testid="phone-country-error" visible when unsupported.
//   AC-NR3.4: purely client-side — no network invocation.
//   AC-US4.1: decision fires within 200ms of input blur (libphonenumber-js sync).
//   AC-US4.2: voice path hidden when unsupported; Telegram path auto-selected.
//   AC-3.3: invalid phone message literal "That number doesn't work. Try again."

const emptyValues: WizardFormValues = {
  location_city: null,
  social_scene: null,
  drug_tolerance: null,
  life_stage: null,
  interest: null,
  name: null,
  age: null,
  occupation: null,
  phone: null,
  chosen_option_id: null,
  cache_key: null,
}

describe("PhoneStep (Step 9) — render + binary path choice", () => {
  it("renders with data-testid='wizard-step-9' (AC-1.5)", () => {
    render(<PhoneStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByTestId("wizard-step-9")).toBeInTheDocument()
  })

  it("renders both path options (voice + text) (FR-1 step 9)", () => {
    render(<PhoneStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(
      screen.getByRole("button", { name: WIZARD_COPY.phone.voiceOption })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: WIZARD_COPY.phone.textOption })
    ).toBeInTheDocument()
  })

  it("shows the tel input only after the voice path is selected", () => {
    render(<PhoneStep values={emptyValues} onAdvance={vi.fn()} />)
    // Before selection — no tel input
    expect(screen.queryByPlaceholderText(WIZARD_COPY.phone.phonePlaceholder)).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.phone.voiceOption }))
    expect(
      screen.getByPlaceholderText(WIZARD_COPY.phone.phonePlaceholder)
    ).toBeInTheDocument()
  })

  it("text path advances immediately with phone=null (auto-advance)", () => {
    const onAdvance = vi.fn()
    render(<PhoneStep values={emptyValues} onAdvance={onAdvance} />)
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.phone.textOption }))
    const cta = screen.getByRole("button", { name: WIZARD_COPY.phone.ctaText })
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledWith({ phone: null })
  })
})

describe("PhoneStep (Step 9) — phone validation (voice path)", () => {
  it("shows Nikita-voiced invalid-format error when the number is not E.164 (AC-3.3)", () => {
    render(<PhoneStep values={emptyValues} onAdvance={vi.fn()} />)
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.phone.voiceOption }))
    const input = screen.getByPlaceholderText(WIZARD_COPY.phone.phonePlaceholder)
    fireEvent.change(input, { target: { value: "not-a-number" } })
    fireEvent.blur(input)
    expect(screen.getByText(WIZARD_COPY.phone.invalidFormatError)).toBeInTheDocument()
  })

  it("shows the unsupported-country message for an unsupported dial code (AC-NR3.1)", () => {
    render(<PhoneStep values={emptyValues} onAdvance={vi.fn()} />)
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.phone.voiceOption }))
    const input = screen.getByPlaceholderText(WIZARD_COPY.phone.phonePlaceholder)
    // +86 (China) is NOT in the SUPPORTED_PHONE_COUNTRIES list.
    fireEvent.change(input, { target: { value: "+8613812345678" } })
    fireEvent.blur(input)
    // data-testid per AC-NR3.3 for Playwright
    expect(screen.getByTestId("phone-country-error")).toBeInTheDocument()
    expect(screen.getByText(WIZARD_COPY.phone.unsupportedCountryError)).toBeInTheDocument()
  })

  it("auto-selects Telegram path when the country is unsupported (AC-US4.2)", () => {
    render(<PhoneStep values={emptyValues} onAdvance={vi.fn()} />)
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.phone.voiceOption }))
    const input = screen.getByPlaceholderText(WIZARD_COPY.phone.phonePlaceholder)
    fireEvent.change(input, { target: { value: "+8613812345678" } })
    fireEvent.blur(input)
    // CTA must now be the Telegram path CTA (not the voice CTA)
    expect(
      screen.getByRole("button", { name: WIZARD_COPY.phone.ctaText })
    ).toBeInTheDocument()
  })

  it("voice path advances with phone=<e164> when number is valid + supported country", () => {
    const onAdvance = vi.fn()
    render(<PhoneStep values={emptyValues} onAdvance={onAdvance} />)
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.phone.voiceOption }))
    const input = screen.getByPlaceholderText(WIZARD_COPY.phone.phonePlaceholder)
    // +1 US is supported
    fireEvent.change(input, { target: { value: "+12025550100" } })
    fireEvent.blur(input)
    const cta = screen.getByRole("button", { name: WIZARD_COPY.phone.ctaVoice })
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledWith({ phone: "+12025550100" })
  })
})
