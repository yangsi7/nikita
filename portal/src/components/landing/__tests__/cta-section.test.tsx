import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { CtaSection } from "../cta-section"

describe("CtaSection — T029 AC-REQ-017", () => {
  it("unauthenticated CTA points to Telegram", () => {
    render(<CtaSection isAuthenticated={false} />)
    const links = screen.getAllByRole("link")
    const ctaLink = links.find((l) => l.getAttribute("href")?.includes("t.me") || l.getAttribute("href")?.includes("telegram"))
    expect(ctaLink).toBeInTheDocument()
  })

  it("authenticated CTA points to dashboard", () => {
    render(<CtaSection isAuthenticated={true} />)
    const links = screen.getAllByRole("link")
    const dashLink = links.find((l) => l.getAttribute("href") === "/dashboard")
    expect(dashLink).toBeInTheDocument()
  })

  it("renders H2 heading", () => {
    render(<CtaSection isAuthenticated={false} />)
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument()
  })

  it("renders supporting sub-text", () => {
    render(<CtaSection isAuthenticated={false} />)
    // Sub-text under heading (not heading itself)
    const section = document.querySelector("section")
    expect(section?.textContent?.length).toBeGreaterThan(20)
  })

  it("renders footer copyright with current year", () => {
    render(<CtaSection isAuthenticated={false} />)
    expect(screen.getByText(/© 2026 Nanoleq/i)).toBeInTheDocument()
  })

  it("renders aurora orb decorative divs", () => {
    const { container } = render(<CtaSection isAuthenticated={false} />)
    const orbs = container.querySelectorAll(".aurora-orb")
    expect(orbs.length).toBeGreaterThanOrEqual(2)
  })
})
