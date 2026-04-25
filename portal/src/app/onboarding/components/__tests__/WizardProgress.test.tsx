import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import { WizardProgress } from "@/app/onboarding/components/WizardProgress"

// Spec 214 PR 214-B — T211 (RED)
// Tests: "step N of 7" renders correctly with canonical letter-spaced
// uppercase chrome per `docs/content/wizard-copy.md` (Shared Chrome).

describe("WizardProgress", () => {
  it("renders the canonical 'step N of 7' label for the given step index", () => {
    render(<WizardProgress current={3} total={7} />)
    expect(screen.getByText("step 3 of 7")).toBeInTheDocument()
  })

  it("accepts arbitrary current/total values and renders them verbatim", () => {
    render(<WizardProgress current={1} total={7} />)
    expect(screen.getByText("step 1 of 7")).toBeInTheDocument()
  })

  it("applies the letter-spacing + uppercase chrome classes", () => {
    render(<WizardProgress current={5} total={7} />)
    const el = screen.getByText("step 5 of 7")
    // Chrome per spec FR-2 / Appendix C reference
    // (text-xs tracking-[0.2em] uppercase text-muted-foreground). We do not
    // hard-code every class name — just the letter-spacing + uppercase
    // signifiers that make it visually a step label.
    expect(el.className).toContain("uppercase")
    expect(el.className).toContain("tracking-[0.2em]")
  })
})
