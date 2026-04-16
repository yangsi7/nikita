import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

import { SceneStep } from "@/app/onboarding/steps/SceneStep"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T202 (RED)
// Tests:
//   AC-1.2: CTA disabled until a scene is selected (zod required field)
//   AC-9.4 pattern: button grid uses WAI-ARIA radiogroup semantics — radio-
//          group role, child radio role, one radio focusable (roving tab).
// NOTE: SceneStep wraps the existing SceneSelector primitive, which uses
// Radix RadioGroup — Radix renders role="radiogroup" on the root and
// role="radio" on each item.

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

describe("SceneStep (Step 5) — layout and a11y", () => {
  it("renders with data-testid='wizard-step-5' (AC-1.5)", () => {
    render(<SceneStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByTestId("wizard-step-5")).toBeInTheDocument()
  })

  it("renders the Nikita-voiced headline (FR-3)", () => {
    render(<SceneStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByText(WIZARD_COPY.scene.headline)).toBeInTheDocument()
  })

  it("wraps the scene options in a radiogroup with role='radiogroup'", () => {
    render(<SceneStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByRole("radiogroup")).toBeInTheDocument()
  })

  it("renders one role='radio' per scene option (5 scenes)", () => {
    render(<SceneStep values={emptyValues} onAdvance={vi.fn()} />)
    const radios = screen.getAllByRole("radio")
    expect(radios.length).toBe(5)
  })
})

describe("SceneStep (Step 5) — selection behaviour", () => {
  it("disables the CTA until a scene is chosen (AC-1.2)", () => {
    render(<SceneStep values={emptyValues} onAdvance={vi.fn()} />)
    const cta = screen.getByRole("button", { name: WIZARD_COPY.scene.cta })
    expect(cta).toBeDisabled()
  })

  it("enables the CTA after a scene is selected (Radix radiogroup keyboard-accessible)", () => {
    render(<SceneStep values={emptyValues} onAdvance={vi.fn()} />)
    const radios = screen.getAllByRole("radio")
    fireEvent.click(radios[0])
    const cta = screen.getByRole("button", { name: WIZARD_COPY.scene.cta })
    expect(cta).not.toBeDisabled()
  })

  it("advances with the chosen social_scene when the CTA is clicked (AC-6.2)", () => {
    const onAdvance = vi.fn()
    render(<SceneStep values={emptyValues} onAdvance={onAdvance} />)
    const radios = screen.getAllByRole("radio")
    // Click the third radio button — Radix `value` attribute pins which
    // scene was selected; SceneStep forwards the value to onAdvance.
    fireEvent.click(radios[2])
    const cta = screen.getByRole("button", { name: WIZARD_COPY.scene.cta })
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledTimes(1)
    const patch = onAdvance.mock.calls[0][0]
    // Must include a social_scene key
    expect(patch).toHaveProperty("social_scene")
    expect(typeof patch.social_scene).toBe("string")
    expect(patch.social_scene.length).toBeGreaterThan(0)
  })
})
