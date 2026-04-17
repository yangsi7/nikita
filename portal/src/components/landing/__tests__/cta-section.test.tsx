import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { CtaSection } from "../cta-section"

describe("CtaSection — T029 AC-REQ-017", () => {
  // Spec 214 PR #310 (AC-US1.1): anon footer CTA must enter the cinematic
  // wizard funnel via /onboarding/auth (FR-1 step 2 magic-link page), NOT
  // bypass to the Telegram bot — that bypass left the entire 11-step
  // wizard unreachable from public traffic until this PR.
  it("unauthenticated CTA points to /onboarding/auth (wizard entry)", () => {
    render(<CtaSection isAuthenticated={false} />)
    const links = screen.getAllByRole("link")
    const ctaLink = links.find((l) => l.getAttribute("href") === "/onboarding/auth")
    expect(ctaLink).toBeInTheDocument()
    const telegramLink = links.find((l) => l.getAttribute("href")?.includes("t.me"))
    expect(telegramLink).toBeUndefined()
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

  it("renders supporting sub-text consistent with the door/funnel motif", () => {
    render(<CtaSection isAuthenticated={false} />)
    // Spec 214 PR #310: copy must NOT promise Telegram — CTA now opens the
    // /onboarding/auth magic-link page ("There's a door. Drop your address.").
    expect(screen.getByText(/the other side of the door/i)).toBeInTheDocument()
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

  it("renders intimate mood backdrop image", () => {
    const { container } = render(<CtaSection isAuthenticated={false} />)
    // Decorative backdrop — empty alt, src contains "intimate"
    const backdrops = container.querySelectorAll('img[alt=""]')
    const intimateBackdrop = Array.from(backdrops).find((img) =>
      img.getAttribute("src")?.includes("intimate")
    )
    expect(intimateBackdrop).toBeInTheDocument()
  })
})
