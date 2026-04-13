import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Spec 212 PR A — "Contact" label must be present in the scroll progress nav

// Mock IntersectionObserver (not available in jsdom)
const observeMock = vi.fn()
const disconnectMock = vi.fn()
globalThis.IntersectionObserver = vi.fn().mockImplementation((cb) => ({
  observe: observeMock,
  disconnect: disconnectMock,
  unobserve: vi.fn(),
  root: null,
  rootMargin: "",
  thresholds: [],
  takeRecords: () => [],
})) as unknown as typeof IntersectionObserver

// Mock getElementById/querySelector for section nodes (they won't exist in jsdom)
vi.spyOn(document, "querySelector").mockImplementation(() => null)

import { ScrollProgress } from "@/app/onboarding/components/scroll-progress"

describe("ScrollProgress — Contact label (Spec 212 PR A)", () => {
  it("includes Contact in the profile section aria-label", () => {
    render(<ScrollProgress />)
    // The profile section nav dot should have an aria-label that contains "Contact"
    // Targeted assertion: find any button whose label matches
    const buttons = screen.getAllByRole("button")
    const contactButton = buttons.find(
      (btn) =>
        btn.getAttribute("aria-label")?.includes("Contact") ?? false
    )
    expect(contactButton).toBeDefined()
  })
})
