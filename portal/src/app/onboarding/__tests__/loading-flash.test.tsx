import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import OnboardingLoading from "../loading"

/**
 * Spec 217-1 FR-3 / AC-3.2, AC-3.4 — onboarding suspense fallback uses
 * Spec 208 brand veil + shadcn Skeleton matching wizard card silhouette.
 *
 * The flash root cause (AC-3.1) is the Next.js suspense fallback at
 * `loading.tsx` flashing "NIKITA IS COMING..." copy + bespoke pulse rows.
 * Replacement: brand-veil background (bg-void) + `<Skeleton>` rows
 * matching the wizard chat-card silhouette, no chatty placeholder copy.
 */
describe("Spec 217-1 FR-3 — onboarding loading.tsx flash remediation", () => {
  it("AC-3.4: does NOT contain placeholder/chatty copy", () => {
    const { container } = render(<OnboardingLoading />)
    expect(container.textContent ?? "").not.toMatch(
      /in development|in progress|NIKITA IS COMING/i,
    )
  })

  it("AC-3.2: renders brand veil (bg-void)", () => {
    const { container } = render(<OnboardingLoading />)
    expect(container.querySelector(".bg-void")).toBeInTheDocument()
  })

  it("AC-3.2: renders shadcn Skeleton (data-slot='skeleton')", () => {
    const { container } = render(<OnboardingLoading />)
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("preserves a11y role=status + aria-live=polite", () => {
    const { container } = render(<OnboardingLoading />)
    const status = container.querySelector('[role="status"]')
    expect(status).toBeInTheDocument()
    expect(status?.getAttribute("aria-live")).toBe("polite")
  })
})
