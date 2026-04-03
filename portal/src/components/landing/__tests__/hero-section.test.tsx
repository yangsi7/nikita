import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroSection } from "../hero-section"

describe("HeroSection — T021 AC-REQ-013", () => {
  it("renders correct H1 text", () => {
    render(<HeroSection isAuthenticated={false} />)
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Don't Get.*Dumped|Don't Get Dumped/i)
  })

  it("renders eyebrow text", () => {
    render(<HeroSection isAuthenticated={false} />)
    expect(screen.getByText(/18\+/)).toBeInTheDocument()
    expect(screen.getByText(/watching/i)).toBeInTheDocument()
  })

  it("renders subheadline with exact copy", () => {
    render(<HeroSection isAuthenticated={false} />)
    expect(screen.getByText(/She remembers everything/i)).toBeInTheDocument()
    expect(screen.getByText(/leave you/i)).toBeInTheDocument()
  })

  it("unauthenticated CTA points to Telegram", () => {
    render(<HeroSection isAuthenticated={false} />)
    const links = screen.getAllByRole("link")
    const ctaLink = links.find((l) => l.getAttribute("href")?.includes("t.me") || l.getAttribute("href")?.includes("telegram"))
    expect(ctaLink).toBeInTheDocument()
  })

  it("authenticated CTA points to dashboard", () => {
    render(<HeroSection isAuthenticated={true} />)
    const links = screen.getAllByRole("link")
    const dashLink = links.find((l) => l.getAttribute("href") === "/dashboard")
    expect(dashLink).toBeInTheDocument()
  })

  it("renders canvas for FallingPattern background", () => {
    const { container } = render(<HeroSection isAuthenticated={false} />)
    const canvas = container.querySelector("canvas")
    expect(canvas).toBeInTheDocument()
  })

  it("hero image has descriptive alt text", () => {
    render(<HeroSection isAuthenticated={false} />)
    const img = screen.getByAltText(/nikita/i)
    expect(img).toBeInTheDocument()
  })
})
