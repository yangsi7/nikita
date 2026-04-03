import { describe, it, expect, vi, beforeEach } from "vitest"
import { render } from "@testing-library/react"
import { FallingPattern } from "../falling-pattern"

// Canvas mock — jsdom does not implement canvas
beforeEach(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    measureText: vi.fn().mockReturnValue({ width: 10 }),
    createLinearGradient: vi.fn().mockReturnValue({
      addColorStop: vi.fn(),
    }),
  })
})

describe("FallingPattern — T009 AC-REQ-009", () => {
  it("renders a canvas element", () => {
    const { container } = render(<FallingPattern />)
    const canvas = container.querySelector("canvas")
    expect(canvas).toBeInTheDocument()
  })

  it("canvas is aria-hidden (decorative)", () => {
    const { container } = render(<FallingPattern />)
    const canvas = container.querySelector("canvas")
    expect(canvas).toHaveAttribute("aria-hidden", "true")
  })

  it("canvas has pointer-events-none to avoid interaction blocking", () => {
    const { container } = render(<FallingPattern />)
    const canvas = container.querySelector("canvas")
    expect(canvas?.className).toMatch(/pointer-events-none/)
  })

  it("canvas is position fixed or absolute to fill background", () => {
    const { container } = render(<FallingPattern />)
    const canvas = container.querySelector("canvas")
    expect(canvas?.className).toMatch(/fixed|absolute|inset/)
  })

  it("respects prefers-reduced-motion — matchMedia queried on mount", () => {
    const matchMediaSpy = vi.spyOn(window, "matchMedia")
    render(<FallingPattern />)
    expect(matchMediaSpy).toHaveBeenCalledWith(
      expect.stringContaining("prefers-reduced-motion")
    )
  })

  it("does not call requestAnimationFrame when reduced motion is active", () => {
    // Override matchMedia to return reduced motion = true
    vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
      matches: query.includes("reduce"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    const rafSpy = vi.spyOn(window, "requestAnimationFrame")
    render(<FallingPattern />)
    expect(rafSpy).not.toHaveBeenCalled()
  })
})
