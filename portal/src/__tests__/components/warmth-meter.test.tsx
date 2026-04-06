/**
 * Tests for WarmthMeter component
 * Verifies percentage display, label text, and progressbar role
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { WarmthMeter } from "@/components/dashboard/warmth-meter"

describe("WarmthMeter", () => {
  it("renders percentage from value prop", () => {
    render(<WarmthMeter value={0.72} />)
    expect(screen.getByText("72%")).toBeInTheDocument()
  })

  it("renders 'Hot' label for high values", () => {
    render(<WarmthMeter value={0.9} />)
    expect(screen.getByText("Hot")).toBeInTheDocument()
    expect(screen.getByText("90%")).toBeInTheDocument()
  })

  it("renders 'Cold' label for low values", () => {
    render(<WarmthMeter value={0.1} />)
    expect(screen.getByText("Cold")).toBeInTheDocument()
    expect(screen.getByText("10%")).toBeInTheDocument()
  })

  it("renders 'Neutral' label for mid-range values", () => {
    render(<WarmthMeter value={0.5} />)
    expect(screen.getByText("Neutral")).toBeInTheDocument()
  })

  it("renders 'Warm' label", () => {
    render(<WarmthMeter value={0.75} />)
    expect(screen.getByText("Warm")).toBeInTheDocument()
  })

  it("renders 'Cool' label", () => {
    render(<WarmthMeter value={0.3} />)
    expect(screen.getByText("Cool")).toBeInTheDocument()
  })

  it("renders progressbar with correct aria attributes", () => {
    render(<WarmthMeter value={0.65} />)
    const bar = screen.getByRole("progressbar")
    expect(bar).toHaveAttribute("aria-valuenow", "65")
    expect(bar).toHaveAttribute("aria-valuemin", "0")
    expect(bar).toHaveAttribute("aria-valuemax", "100")
    // 0.65 >= 0.6 threshold → "Warm"
    expect(bar).toHaveAttribute("aria-label", "Warmth: 65% (Warm)")
  })

  it("renders Warmth heading", () => {
    render(<WarmthMeter value={0.5} />)
    expect(screen.getByText("Warmth")).toBeInTheDocument()
  })
})
