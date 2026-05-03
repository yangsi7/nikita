import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { NikitaReaction } from "@/app/onboarding/_components/NikitaReaction"

describe("NikitaReaction — AC C1.9 / C1.20", () => {
  it("renders the reaction text", () => {
    render(<NikitaReaction text="zürich. okay." />)
    expect(screen.getByText(/zürich\. okay\./)).toBeInTheDocument()
  })

  it("wraps text in an aria-live polite region (atomic)", () => {
    render(<NikitaReaction text="hello." />)
    const node = screen.getByText(/hello\./)
    expect(node).toHaveAttribute("aria-live", "polite")
    expect(node).toHaveAttribute("aria-atomic", "true")
  })
})
