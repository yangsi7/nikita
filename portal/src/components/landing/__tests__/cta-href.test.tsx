import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroSection } from "../hero-section"
import { CtaSection } from "../cta-section"

/**
 * Spec 220 ADR-220-1 — CTA static `?start=new` (canonical entry point).
 *
 * ?start=new signals a fresh signup flow to the bot's /start handler.
 * Telegram renders the START button for deep-links regardless of payload value.
 */
describe("Spec 220 ADR-220-1 — TG-first CTA carries ?start=new", () => {
  function findTelegramHref(): URL | undefined {
    const links = screen.getAllByRole("link")
    const ctaLink = links.find((l) =>
      l.getAttribute("href")?.startsWith("https://t.me/"),
    )
    if (!ctaLink) return undefined
    return new URL(ctaLink.getAttribute("href")!)
  }

  it("hero-section anon CTA URL.searchParams.start === 'new'", () => {
    render(<HeroSection isAuthenticated={false} />)
    const url = findTelegramHref()
    expect(url).toBeDefined()
    expect(url!.host).toBe("t.me")
    expect(url!.pathname).toBe("/Nikita_my_bot")
    expect(url!.searchParams.get("start")).toBe("new")
  })

  it("cta-section anon CTA URL.searchParams.start === 'new'", () => {
    render(<CtaSection isAuthenticated={false} />)
    const url = findTelegramHref()
    expect(url).toBeDefined()
    expect(url!.host).toBe("t.me")
    expect(url!.pathname).toBe("/Nikita_my_bot")
    expect(url!.searchParams.get("start")).toBe("new")
  })

  it("hero-section authenticated CTA does NOT contain ?start=new (still /dashboard)", () => {
    render(<HeroSection isAuthenticated={true} />)
    const links = screen.getAllByRole("link")
    const dashLink = links.find((l) => l.getAttribute("href") === "/dashboard")
    expect(dashLink).toBeInTheDocument()
    // Authenticated branch must NOT silently route to t.me
    const tgLink = links.find((l) =>
      l.getAttribute("href")?.startsWith("https://t.me/"),
    )
    expect(tgLink).toBeUndefined()
  })

  it("cta-section authenticated CTA does NOT contain ?start=new (still /dashboard)", () => {
    render(<CtaSection isAuthenticated={true} />)
    const links = screen.getAllByRole("link")
    const dashLink = links.find((l) => l.getAttribute("href") === "/dashboard")
    expect(dashLink).toBeInTheDocument()
    const tgLink = links.find((l) =>
      l.getAttribute("href")?.startsWith("https://t.me/"),
    )
    expect(tgLink).toBeUndefined()
  })
})
