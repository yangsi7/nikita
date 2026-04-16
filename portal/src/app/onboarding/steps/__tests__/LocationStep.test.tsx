import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

// Mock the onboarding API hook so the venue-preview call is observable without
// touching the real apiClient transport.
vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => {
  return {
    useOnboardingAPI: () => ({
      previewBackstory: previewBackstoryMock,
      submitProfile: vi.fn(),
      patchProfile: vi.fn(),
      selectBackstory: vi.fn(),
    }),
  }
})

let previewBackstoryMock = vi.fn()

import { LocationStep } from "@/app/onboarding/steps/LocationStep"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T201 (RED)
// Tests:
//   AC-4.0: step 4 inline venue preview calls POST /preview-backstory on blur
//            with a minimal payload (city only, other fields null/default).
//   AC-6.2: step 4 CTA advances with { location_city }.
//   AC-NR2.3: nothing here; name/age/occupation live in step 7.

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

describe("LocationStep (Step 4)", () => {
  beforeEach(() => {
    previewBackstoryMock = vi.fn().mockResolvedValue({
      scenarios: [],
      venues_used: ["Berghain", "Kit Kat"],
      cache_key: "k1",
      degraded: true,
    })
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("renders with data-testid='wizard-step-4' (AC-1.5)", () => {
    render(<LocationStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByTestId("wizard-step-4")).toBeInTheDocument()
  })

  it("renders the Nikita-voiced headline + placeholder (FR-3)", () => {
    render(<LocationStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByText(WIZARD_COPY.location.headline)).toBeInTheDocument()
    const input = screen.getByPlaceholderText(WIZARD_COPY.location.placeholder)
    expect(input).toBeInTheDocument()
  })

  it("fires the venue-preview request after the debounce window on blur (AC-4.0)", async () => {
    render(<LocationStep values={emptyValues} onAdvance={vi.fn()} />)
    const input = screen.getByPlaceholderText(WIZARD_COPY.location.placeholder)
    fireEvent.change(input, { target: { value: "Berlin" } })
    fireEvent.blur(input)
    // The component debounces the call 800ms
    await vi.advanceTimersByTimeAsync(800)
    expect(previewBackstoryMock).toHaveBeenCalledTimes(1)
    expect(previewBackstoryMock).toHaveBeenCalledWith(
      expect.objectContaining({ city: "Berlin" })
    )
    // Other fields must be null or sentinel — minimal payload
    const arg = previewBackstoryMock.mock.calls[0][0]
    expect(arg.age).toBeNull()
    expect(arg.occupation).toBeNull()
    expect(arg.life_stage).toBeNull()
    expect(arg.interest).toBeNull()
  })

  it("renders venue names below the input after the preview resolves (AC-4.0)", async () => {
    render(<LocationStep values={emptyValues} onAdvance={vi.fn()} />)
    const input = screen.getByPlaceholderText(WIZARD_COPY.location.placeholder)
    fireEvent.change(input, { target: { value: "Berlin" } })
    fireEvent.blur(input)
    await vi.advanceTimersByTimeAsync(800)
    // Yield microtasks so the resolved promise lands
    await vi.runAllTimersAsync()
    await waitFor(() => {
      expect(screen.getByText(/Berghain/)).toBeInTheDocument()
      expect(screen.getByText(/Kit Kat/)).toBeInTheDocument()
    })
  })

  it("advances via the CTA with the location_city patch (AC-6.2)", () => {
    const onAdvance = vi.fn()
    render(<LocationStep values={emptyValues} onAdvance={onAdvance} />)
    const input = screen.getByPlaceholderText(WIZARD_COPY.location.placeholder)
    fireEvent.change(input, { target: { value: "Berlin" } })
    const cta = screen.getByRole("button", { name: WIZARD_COPY.location.cta })
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledWith({ location_city: "Berlin" })
  })

  it("disables the CTA until the city field has at least 2 characters (AC-1.2)", () => {
    render(<LocationStep values={emptyValues} onAdvance={vi.fn()} />)
    const cta = screen.getByRole("button", { name: WIZARD_COPY.location.cta })
    expect(cta).toBeDisabled()
    const input = screen.getByPlaceholderText(WIZARD_COPY.location.placeholder)
    fireEvent.change(input, { target: { value: "B" } })
    expect(cta).toBeDisabled()
    fireEvent.change(input, { target: { value: "Berlin" } })
    expect(cta).not.toBeDisabled()
  })
})
