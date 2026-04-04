/**
 * Tests for RelativeTime component (hydration-safe time display)
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render } from "@testing-library/react"
import { RelativeTime } from "@/components/shared/relative-time"

describe("RelativeTime", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders a span element", () => {
    const { container } = render(<RelativeTime date="2026-03-10T12:00:00Z" />)
    const span = container.querySelector("span")
    expect(span).toBeInTheDocument()
  })

  it("renders with a Date object", () => {
    const { container } = render(<RelativeTime date={new Date("2026-03-10T12:00:00Z")} />)
    const span = container.querySelector("span")
    expect(span).toBeInTheDocument()
  })

  it("renders formatted date text", () => {
    const { container } = render(<RelativeTime date="2026-03-10T12:00:00Z" />)
    const span = container.querySelector("span")
    // formatDate returns "Mar 10, 2026" — assert recognizable substring
    expect(span?.textContent).toMatch(/Mar\s+10/)
  })

  it("applies custom className", () => {
    const { container } = render(<RelativeTime date="2026-03-10T12:00:00Z" className="text-red-500" />)
    const span = container.querySelector("span")
    expect(span?.className).toContain("text-red-500")
  })

  it("displays different text for recent vs old dates", () => {
    const recentDate = new Date(Date.now() - 60_000).toISOString() // 1 min ago
    const oldDate = "2025-01-01T00:00:00Z"

    const { container: recentContainer } = render(<RelativeTime date={recentDate} />)
    const { container: oldContainer } = render(<RelativeTime date={oldDate} />)

    const recentText = recentContainer.querySelector("span")?.textContent
    const oldText = oldContainer.querySelector("span")?.textContent

    // Recent date → relative like "1m ago"; old date → absolute like "Jan 1, 2025"
    expect(recentText).toMatch(/\d+m ago|just now/)
    expect(oldText).toMatch(/Jan\s+1/)
  })
})
