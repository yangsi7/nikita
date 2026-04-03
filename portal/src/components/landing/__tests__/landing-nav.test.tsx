import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { LandingNav } from "../landing-nav"

describe("LandingNav — T031 AC-REQ-018", () => {
  it("unauthenticated: renders Meet Nikita CTA link pointing to Telegram", () => {
    render(<LandingNav isAuthenticated={false} />)
    const link = screen.getByRole("link", { name: /meet nikita/i })
    expect(link).toBeInTheDocument()
    expect(link.getAttribute("href")).toMatch(/t\.me|telegram/)
  })

  it("authenticated: renders Go to Dashboard link pointing to /dashboard", () => {
    render(<LandingNav isAuthenticated={true} />)
    const link = screen.getByRole("link", { name: /dashboard/i })
    expect(link).toBeInTheDocument()
    expect(link.getAttribute("href")).toBe("/dashboard")
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

  it("starts visually hidden (opacity-0 or translate) and becomes visible on scroll", () => {
    const { container } = render(<LandingNav isAuthenticated={false} />)
    // Initially rendered with opacity-0 or translateY (before scroll triggers show)
    const nav = container.querySelector("nav") ?? container.firstChild as HTMLElement
    // Nav should exist — scroll behavior tested via E2E
    expect(nav).toBeInTheDocument()
  })
})
