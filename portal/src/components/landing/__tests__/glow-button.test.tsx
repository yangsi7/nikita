import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { GlowButton } from "../glow-button"

// framer-motion globally mocked in vitest.setup.ts

describe("GlowButton — T007 AC-REQ-007", () => {
  it("renders with correct text as a link", () => {
    render(<GlowButton href="/test">Start Now</GlowButton>)
    const link = screen.getByRole("link", { name: /start now/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/test")
  })

  it("renders ArrowUpRight icon for external href", () => {
    render(<GlowButton href="https://t.me/nikita">Join</GlowButton>)
    // ArrowUpRight renders as svg from lucide-react
    const svg = document.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })

  it("has glow-rose-pulse class on the button element", () => {
    render(<GlowButton href="/test">CTA</GlowButton>)
    const link = screen.getByRole("link")
    expect(link).toHaveClass("glow-rose-pulse")
  })

  it("has rounded-full styling", () => {
    render(<GlowButton href="/test">CTA</GlowButton>)
    const link = screen.getByRole("link")
    expect(link.className).toMatch(/rounded-full/)
  })

  it("applies size variant classes", () => {
    const { rerender } = render(<GlowButton href="/test" size="sm">Small</GlowButton>)
    expect(screen.getByRole("link").className).toMatch(/text-sm/)
    rerender(<GlowButton href="/test" size="lg">Large</GlowButton>)
    expect(screen.getByRole("link").className).toMatch(/text-lg/)
  })

  it("applies bg-primary class", () => {
    render(<GlowButton href="/test">CTA</GlowButton>)
    const link = screen.getByRole("link")
    expect(link.className).toMatch(/bg-primary/)
  })

  it("passes additional className", () => {
    render(<GlowButton href="/test" className="custom-class">CTA</GlowButton>)
    expect(screen.getByRole("link")).toHaveClass("custom-class")
  })
})
