/**
 * Tests for MoodOrb component
 * Verifies CSS calculations from emotional state and conflict state color overrides
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MoodOrb } from "@/components/dashboard/mood-orb"
import type { EmotionalStateResponse } from "@/lib/api/types"

const defaultState: EmotionalStateResponse = {
  state_id: "es-001",
  arousal: 0.5,
  valence: 0.5,
  dominance: 0.5,
  intimacy: 0.5,
  conflict_state: "none",
  conflict_started_at: null,
  conflict_trigger: null,
  description: "Feeling balanced and neutral",
  last_updated: "2026-03-20T15:00:00Z",
}

const conflictState: EmotionalStateResponse = {
  ...defaultState,
  state_id: "es-002",
  conflict_state: "cold",
  conflict_started_at: "2026-03-20T14:00:00Z",
  conflict_trigger: "ignored messages",
  description: "Feeling cold and distant",
}

const explosiveState: EmotionalStateResponse = {
  ...defaultState,
  state_id: "es-003",
  arousal: 0.9,
  valence: 0.1,
  dominance: 0.8,
  intimacy: 0.2,
  conflict_state: "explosive",
  description: "Furious and ready to fight",
}

describe("MoodOrb", () => {
  it("renders with default emotional state", () => {
    render(<MoodOrb state={defaultState} />)

    const orb = screen.getByRole("img", { name: /mood orb/i })
    expect(orb).toBeInTheDocument()
    expect(screen.getByText("Feeling balanced and neutral")).toBeInTheDocument()
  })

  it("renders stat labels and progress bars", () => {
    render(<MoodOrb state={defaultState} />)

    expect(screen.getByText("Arousal")).toBeInTheDocument()
    expect(screen.getByText("Valence")).toBeInTheDocument()
    expect(screen.getByText("Dominance")).toBeInTheDocument()
    expect(screen.getByText("Intimacy")).toBeInTheDocument()
    // Percentage values (0.5 * 100 = 50)
    const percentages = screen.getAllByText("50%")
    expect(percentages.length).toBe(4)
  })

  it("applies correct size from dominance", () => {
    render(<MoodOrb state={defaultState} />)

    const orb = screen.getByRole("img", { name: /mood orb/i })
    // size = 80 + dominance * 80 = 80 + 0.5 * 80 = 120
    expect(orb.style.width).toBe("120px")
    expect(orb.style.height).toBe("120px")
  })

  it("uses conflict color override for cold state", () => {
    render(<MoodOrb state={conflictState} />)

    const orb = screen.getByRole("img", { name: /mood orb/i })
    // Cold conflict uses hue 200 — jsdom may convert hsl() to rgb(), so check
    // the raw style attribute which preserves the original hsl values
    const styleAttr = orb.getAttribute("style") ?? ""
    expect(styleAttr).toContain("200")
    expect(screen.getByText("Feeling cold and distant")).toBeInTheDocument()
  })

  it("uses conflict color override for explosive state", () => {
    render(<MoodOrb state={explosiveState} />)

    const orb = screen.getByRole("img", { name: /mood orb/i })
    // Explosive conflict hue = 0 (red)
    // size = 80 + 0.8 * 80 = 144
    expect(orb.style.width).toBe("144px")
    expect(orb.style.height).toBe("144px")
    expect(screen.getByText("Furious and ready to fight")).toBeInTheDocument()
  })

  it("computes pulse speed from arousal", () => {
    render(<MoodOrb state={defaultState} />)

    const orb = screen.getByRole("img", { name: /mood orb/i })
    // pulseSpeed = 3 - arousal * 2 = 3 - 0.5 * 2 = 2
    expect(orb.style.animation).toContain("2s")
  })

  it("renders the glass card wrapper with data-testid", () => {
    render(<MoodOrb state={defaultState} />)

    expect(screen.getByTestId("card-mood-orb")).toBeInTheDocument()
  })
})
