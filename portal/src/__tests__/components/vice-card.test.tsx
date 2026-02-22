/**
 * Tests for ViceCard and ViceLockedCard components
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ViceCard, ViceLockedCard } from "@/components/dashboard/vice-card"
import type { VicePreference } from "@/lib/api/types"

const mockVice: VicePreference = {
  category: "dark_humor",
  intensity_level: 3,
  engagement_score: 0.78,
  discovered_at: "2026-02-01T10:00:00Z",
}

describe("ViceCard", () => {
  it("renders vice category with underscores replaced", () => {
    render(<ViceCard vice={mockVice} />)
    expect(screen.getByText("dark humor")).toBeInTheDocument()
  })

  it("renders engagement score as percentage", () => {
    render(<ViceCard vice={mockVice} />)
    expect(screen.getByText("Engagement: 78%")).toBeInTheDocument()
  })

  it("renders 5 intensity bars", () => {
    const { container } = render(<ViceCard vice={mockVice} />)
    // Each bar is a div with h-1.5 and w-4
    const bars = container.querySelectorAll(".h-1\\.5.w-4")
    expect(bars).toHaveLength(5)
  })

  it("renders at intensity level 1", () => {
    const vice: VicePreference = { ...mockVice, intensity_level: 1 }
    render(<ViceCard vice={vice} />)
    expect(screen.getByText("Engagement: 78%")).toBeInTheDocument()
  })

  it("renders at intensity level 5", () => {
    const vice: VicePreference = { ...mockVice, intensity_level: 5 }
    render(<ViceCard vice={vice} />)
    expect(screen.getByText("dark humor")).toBeInTheDocument()
  })

  it("renders single-word category correctly", () => {
    const vice: VicePreference = { ...mockVice, category: "romance" }
    render(<ViceCard vice={vice} />)
    expect(screen.getByText("romance")).toBeInTheDocument()
  })
})

describe("ViceLockedCard", () => {
  it("renders undiscovered label", () => {
    render(<ViceLockedCard />)
    expect(screen.getByText("Undiscovered")).toBeInTheDocument()
  })

  it("renders 'Talk more to discover' hint", () => {
    render(<ViceLockedCard />)
    expect(screen.getByText("Talk more to discover")).toBeInTheDocument()
  })

  it("renders 5 empty bars", () => {
    const { container } = render(<ViceLockedCard />)
    const bars = container.querySelectorAll(".h-1\\.5.w-4")
    expect(bars).toHaveLength(5)
  })
})
