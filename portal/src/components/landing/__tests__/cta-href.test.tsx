import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroSection } from "../hero-section"
import { CtaSection } from "../cta-section"

/**
 * Spec 217-1 FR-1 / AC-1.1, AC-1.2, AC-1.3 — cold-start CTA static `?start=welcome`.
 *
 * Telegram clients render the START button (instead of typing the bot's name)
 * only when `t.me/<bot>?start=<payload>` deep-links arrive with a payload.
 * Without the payload, returning users with chat history skip the START button
 * and the bot's `/start` handler never fires — breaking the cold-start funnel.
 *
 * The append uses `URL`/`URLSearchParams` so any pre-existing UTM tags or
 * tracking params survive (parse-safe, not naive concat).
 */
describe("Spec 217-1 FR-1 — TG-first CTA carries ?start=welcome", () => {
  function findTelegramHref(): URL | undefined {
    const links = screen.getAllByRole("link")
    const ctaLink = links.find((l) =>
      l.getAttribute("href")?.startsWith("https://t.me/"),
    )
    if (!ctaLink) return undefined
    return new URL(ctaLink.getAttribute("href")!)
  }

  it("hero-section anon CTA URL.searchParams.start === 'welcome'", () => {
    render(<HeroSection isAuthenticated={false} />)
    const url = findTelegramHref()
    expect(url).toBeDefined()
    expect(url!.host).toBe("t.me")
    expect(url!.pathname).toBe("/Nikita_my_bot")
    expect(url!.searchParams.get("start")).toBe("welcome")
  })

  it("cta-section anon CTA URL.searchParams.start === 'welcome'", () => {
    render(<CtaSection isAuthenticated={false} />)
    const url = findTelegramHref()
    expect(url).toBeDefined()
    expect(url!.host).toBe("t.me")
    expect(url!.pathname).toBe("/Nikita_my_bot")
    expect(url!.searchParams.get("start")).toBe("welcome")
  })

  it("hero-section authenticated CTA does NOT contain ?start=welcome (still /dashboard)", () => {
    render(<HeroSection isAuthenticated={true} />)
    const links = screen.getAllByRole("link")
    const dashLink = links.find((l) => l.getAttribute("href") === "/dashboard")
    expect(dashLink).toBeInTheDocument()
    // Authenticated branch must NOT silently route to t.me with payload
    const tgLink = links.find((l) =>
      l.getAttribute("href")?.startsWith("https://t.me/"),
    )
    expect(tgLink).toBeUndefined()
  })

  it("cta-section authenticated CTA does NOT contain ?start=welcome (still /dashboard)", () => {
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
