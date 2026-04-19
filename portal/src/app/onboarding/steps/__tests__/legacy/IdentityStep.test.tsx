import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

import { IdentityStep } from "@/app/onboarding/steps/legacy/IdentityStep"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T204 (RED)
// Tests:
//   AC-NR2.1: three distinct input fields — name / age (min=18 max=99) /
//              occupation (maxLength=100), all optional.
//   AC-NR2.2: skipping is allowed; no validation errors on empty submit.
//   AC-NR2.3: onAdvance payload carries name/age/occupation (null for empty).

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

describe("IdentityStep (Step 7) — render", () => {
  it("renders with data-testid='wizard-step-7' (AC-1.5)", () => {
    render(<IdentityStep values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByTestId("wizard-step-7")).toBeInTheDocument()
  })

  it("renders three inputs — name, age (number), occupation (AC-NR2.1)", () => {
    render(<IdentityStep values={emptyValues} onAdvance={vi.fn()} />)
    const name = screen.getByLabelText(WIZARD_COPY.identity.nameLabel)
    const age = screen.getByLabelText(WIZARD_COPY.identity.ageLabel)
    const occupation = screen.getByLabelText(WIZARD_COPY.identity.occupationLabel)
    expect(name).toBeInTheDocument()
    expect(age).toBeInTheDocument()
    expect(occupation).toBeInTheDocument()
    expect(age).toHaveAttribute("type", "number")
    expect(age).toHaveAttribute("min", "18")
    expect(age).toHaveAttribute("max", "99")
    expect(occupation).toHaveAttribute("maxLength", "100")
  })
})

describe("IdentityStep (Step 7) — validation", () => {
  it("shows the Nikita-voiced age error when age < 18 (FR-3)", () => {
    render(<IdentityStep values={emptyValues} onAdvance={vi.fn()} />)
    const age = screen.getByLabelText(WIZARD_COPY.identity.ageLabel)
    fireEvent.change(age, { target: { value: "16" } })
    fireEvent.blur(age)
    expect(screen.getByText(WIZARD_COPY.identity.ageError)).toBeInTheDocument()
  })

  it("disables the CTA while age < 18 is present (AC-1.2)", () => {
    render(<IdentityStep values={emptyValues} onAdvance={vi.fn()} />)
    const age = screen.getByLabelText(WIZARD_COPY.identity.ageLabel)
    fireEvent.change(age, { target: { value: "15" } })
    const cta = screen.getByRole("button", { name: WIZARD_COPY.identity.cta })
    expect(cta).toBeDisabled()
  })

  it("allows empty-everything advance (all fields optional per AC-NR2.2)", () => {
    const onAdvance = vi.fn()
    render(<IdentityStep values={emptyValues} onAdvance={onAdvance} />)
    const cta = screen.getByRole("button", { name: WIZARD_COPY.identity.cta })
    // No input touched — CTA must NOT be disabled for empty optionals
    expect(cta).not.toBeDisabled()
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledWith({
      name: null,
      age: null,
      occupation: null,
    })
  })
})

describe("IdentityStep (Step 7) — advance with values", () => {
  it("forwards the three field values on CTA click (AC-NR2.3)", () => {
    const onAdvance = vi.fn()
    render(<IdentityStep values={emptyValues} onAdvance={onAdvance} />)
    fireEvent.change(screen.getByLabelText(WIZARD_COPY.identity.nameLabel), {
      target: { value: "Simon" },
    })
    fireEvent.change(screen.getByLabelText(WIZARD_COPY.identity.ageLabel), {
      target: { value: "33" },
    })
    fireEvent.change(screen.getByLabelText(WIZARD_COPY.identity.occupationLabel), {
      target: { value: "engineer" },
    })
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.identity.cta }))
    expect(onAdvance).toHaveBeenCalledWith({
      name: "Simon",
      age: 33,
      occupation: "engineer",
    })
  })
})
