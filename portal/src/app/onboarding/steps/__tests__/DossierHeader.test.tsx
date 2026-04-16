import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

import { DossierHeader } from "@/app/onboarding/steps/DossierHeader"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T200 (RED)
// Tests:
//   AC-1.4: Step 3 shows 50/50/50/50 defaults OR real UserMetrics — never
//            the hardcoded 75/100 that the old Score section used.
//   AC-2.1: Renders classified-file aesthetic with 4 metric bars.
//   AC-1.5: data-testid="wizard-step-3" present on root.

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

describe("DossierHeader (Step 3)", () => {
  it("renders with data-testid='wizard-step-3' on the root (AC-1.5)", () => {
    render(<DossierHeader values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByTestId("wizard-step-3")).toBeInTheDocument()
  })

  it("renders the Nikita-voiced headline and subline (FR-3)", () => {
    render(<DossierHeader values={emptyValues} onAdvance={vi.fn()} />)
    expect(screen.getByText(WIZARD_COPY.dossierHeader.headline)).toBeInTheDocument()
    expect(screen.getByText(WIZARD_COPY.dossierHeader.subline)).toBeInTheDocument()
  })

  it("renders all 4 metric bars with canonical labels (AC-2.1)", () => {
    render(<DossierHeader values={emptyValues} onAdvance={vi.fn()} />)
    for (const label of WIZARD_COPY.dossierHeader.metricLabels) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it("defaults every metric to 50% when no real metrics are supplied (AC-1.4)", () => {
    render(<DossierHeader values={emptyValues} onAdvance={vi.fn()} />)
    // Each bar's percent label should read "50%" — not the legacy 75/100.
    const fifties = screen.getAllByText("50%")
    expect(fifties.length).toBeGreaterThanOrEqual(4)
    // Negative: legacy copy must NOT appear
    expect(screen.queryByText(/75\/100/)).not.toBeInTheDocument()
    expect(screen.queryByText(/75%/)).not.toBeInTheDocument()
  })

  it("shows real metrics when provided via the `metrics` prop (AC-1.4)", () => {
    render(
      <DossierHeader
        values={emptyValues}
        onAdvance={vi.fn()}
        metrics={{ nikita: 62, trust: 44, tension: 30, memory: 20 }}
      />
    )
    expect(screen.getByText("62%")).toBeInTheDocument()
    expect(screen.getByText("44%")).toBeInTheDocument()
    expect(screen.getByText("30%")).toBeInTheDocument()
    expect(screen.getByText("20%")).toBeInTheDocument()
  })

  it("fires onAdvance with an empty patch when the CTA is clicked (AC-1.2)", () => {
    const onAdvance = vi.fn()
    render(<DossierHeader values={emptyValues} onAdvance={onAdvance} />)
    const cta = screen.getByRole("button", { name: WIZARD_COPY.dossierHeader.cta })
    fireEvent.click(cta)
    expect(onAdvance).toHaveBeenCalledWith({})
  })

  it("does NOT leak any forbidden SaaS phrase (FR-3)", () => {
    const { container } = render(<DossierHeader values={emptyValues} onAdvance={vi.fn()} />)
    const text = container.textContent ?? ""
    // "Continue" added 2026-04-16 after QA iter-1 finding I1 — design brief
    // §"What Gets REJECTED" lists it explicitly alongside Get Started / Sign Up.
    expect(text).not.toMatch(/Continue|Get Started|Sign Up|Submit|Processing\.\.\./i)
  })
})
