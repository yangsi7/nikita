import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { LandingNav } from "../landing-nav"

describe("LandingNav — T031 AC-REQ-018", () => {
  // Spec 214 PR #310: anon nav CTA must enter the wizard funnel via
  // /onboarding/auth, not bypass to Telegram bot.
  it("unauthenticated: renders CTA link pointing to /onboarding/auth", () => {
    const { container } = render(<LandingNav isAuthenticated={false} />)
    // Nav starts with visibility:hidden (scroll-triggered), so use DOM queries
    const link = container.querySelector("a[href='/onboarding/auth']")
    expect(link).toBeInTheDocument()
    expect(link?.textContent).toMatch(/start relationship/i)
    // Regression guard: no direct-Telegram bypass for anon
    expect(container.querySelector("a[href*='t.me']")).toBeNull()
  })

  it("authenticated: renders Go to Dashboard link pointing to /dashboard", () => {
    const { container } = render(<LandingNav isAuthenticated={true} />)
    const link = container.querySelector("a[href='/dashboard']")
    expect(link).toBeInTheDocument()
    expect(link?.textContent).toMatch(/dashboard/i)
  })

  it("has fixed positioning class", () => {
    const { container } = render(<LandingNav isAuthenticated={false} />)
    const nav = container.querySelector("nav") ?? container.firstChild as HTMLElement
    expect(nav?.className || container.innerHTML).toMatch(/fixed/)
  })

  it("has glass-card class or backdrop-blur styling", () => {
    const { container } = render(<LandingNav isAuthenticated={false} />)
    const nav = container.querySelector("nav") ?? container.firstChild as HTMLElement
    expect(nav?.className || container.innerHTML).toMatch(/glass-card|backdrop-blur/)
  })

  it("starts visually hidden and becomes visible on scroll", () => {
    const { container } = render(<LandingNav isAuthenticated={false} />)
    const nav = container.querySelector("nav") ?? container.firstChild as HTMLElement
    // Nav starts hidden (visibility:hidden) — prevents keyboard focus on invisible nav
    expect(nav).toBeInTheDocument()
    expect((nav as HTMLElement)?.style.visibility).toBe("hidden")
  })
})
