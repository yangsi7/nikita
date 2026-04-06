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
    expect(screen.getByText(/adults only/i)).toBeInTheDocument()
  })

  it("renders 3-item mechanics row (no BrainCircuit pill)", () => {
    render(<HeroSection isAuthenticated={false} />)
    expect(screen.getByText(/text on telegram/i)).toBeInTheDocument()
    expect(screen.getByText(/talk on the phone/i)).toBeInTheDocument()
    expect(screen.getByText(/monitor your relationship/i)).toBeInTheDocument()
    // "She remembers" pill (BrainCircuit) was removed — covered in PitchSection instead
    expect(screen.queryByText(/she remembers$/i)).not.toBeInTheDocument()
  })

  it("renders MoodStrip with all 9 moods visible on all viewports", () => {
    const { container } = render(<HeroSection isAuthenticated={false} />)
    // MoodStrip is below the grid — NOT inside hidden lg:flex
    const strip = container.querySelector('[aria-label*="mood range"]')
    expect(strip).toBeInTheDocument()
    // All 9 mood thumbnails present — scoped to strip to exclude the hero image
    const moodImgs = strip?.querySelectorAll('img[alt^="Nikita — "]') ?? []
    expect(moodImgs.length).toBe(9)
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
    // Hero has an alt distinct from MoodStrip thumbnails ("Nikita — <mood>")
    const img = screen.getByAltText(/nikita — don't get dumped/i)
    expect(img).toBeInTheDocument()
  })
})
