import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { CtaSection } from "../cta-section"

describe("CtaSection — T029 AC-REQ-017", () => {
  // Spec 216-G: anon footer CTA goes straight to Telegram. signup_handler
  // FSM walks the user through email + magic-link, /auth/confirm autobinds
  // users.telegram_id atomically. Portal-first /onboarding/auth removed.
  it("unauthenticated CTA points to Telegram bot (TG-first canonical entry)", () => {
    render(<CtaSection isAuthenticated={false} />)
    const links = screen.getAllByRole("link")
    const ctaLink = links.find(
      (l) => l.getAttribute("href") === "https://t.me/Nikita_my_bot",
    )
    expect(ctaLink).toBeInTheDocument()
    const portalAuth = links.find(
      (l) => l.getAttribute("href") === "/onboarding/auth",
    )
    expect(portalAuth).toBeUndefined()
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
    // Spec 216-G: copy stays evocative; CTA target is now Telegram.
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
