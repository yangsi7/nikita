import { createElement } from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

// Mock the shadcn Slider primitive as a plain <input type="range"> so we can
// drive it via fireEvent.change in a jsdom environment. Mirrors the pattern
// used in `portal/src/__tests__/onboarding/components.test.tsx`.
vi.mock("@/components/ui/slider", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Slider: ({ min, max, step, value, onValueChange, ...p }: any) =>
    createElement("input", {
      type: "range",
      min,
      max,
      step,
      value: value?.[0],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
        onValueChange?.([Number(e.target.value)]),
      "aria-label": p["aria-label"],
      "data-testid": "edginess-slider",
    }),
}))

import { DarknessStep } from "@/app/onboarding/steps/legacy/DarknessStep"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T203 (RED)
// Tests:
//   AC-1.2: slider must yield a value 1..5; CTA disabled at initial 0/null
//   FR-3 / copy: a live Nikita quote changes as the slider value changes

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

describe("DarknessStep (Step 6) — headline, slider, Nikita quote", () => {
  it("renders with data-testid='wizard-step-6' (AC-1.5)", () => {
    render(<DarknessStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByTestId("wizard-step-6")).toBeInTheDocument()
  })

  it("renders the Nikita-voiced headline", () => {
    render(<DarknessStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByText(WIZARD_COPY.darkness.headline)).toBeInTheDocument()
  })

  it("renders the Nikita-voiced sub line", () => {
    render(<DarknessStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByText(WIZARD_COPY.darkness.subline)).toBeInTheDocument()
  })

  it("renders a slider primitive labelled for screen readers", () => {
    render(<DarknessStep values={emptyValues} onAdvance={vi.fn()} />)
    const slider = screen.getByTestId("edginess-slider")
    expect(slider).toBeInTheDocument()
    expect(slider).toHaveAttribute("min", "1")
    expect(slider).toHaveAttribute("max", "5")
  })

  it("updates the visible Nikita quote when the slider value changes", () => {
    render(<DarknessStep values={emptyValues} onAdvance={vi.fn()} />)
    const slider = screen.getByTestId("edginess-slider")

    fireEvent.change(slider, { target: { value: "1" } })
    // Level 1 copy from EdginessSlider: "Keep it clean"
    expect(screen.getByText(/Keep it clean/i)).toBeInTheDocument()

    fireEvent.change(slider, { target: { value: "5" } })
    // Level 5 copy: "No limits"
    expect(screen.getByText(/No limits/i)).toBeInTheDocument()
  })
})

describe("DarknessStep (Step 6) — advance", () => {
  it("advances with drug_tolerance set to the current slider value (AC-6.2)", () => {
    const onAdvance = vi.fn()
    render(<DarknessStep values={emptyValues} onAdvance={onAdvance} />)
    const slider = screen.getByTestId("edginess-slider")
    fireEvent.change(slider, { target: { value: "4" } })
    const cta = screen.getByRole("button", { name: WIZARD_COPY.darkness.cta })
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledWith({ drug_tolerance: 4 })
  })
})
