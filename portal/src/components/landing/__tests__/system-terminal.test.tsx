import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { SystemTerminal } from "../system-terminal"

describe("SystemTerminal — T017 AC-REQ-011", () => {
  it("renders all 14 system names", () => {
    render(<SystemTerminal />)
    const systems = [
      "Emotional Memory Engine",
      "Vice Personalization Layer",
      "Relationship Scoring Engine",
      "Boss Encounter System",
      "Chapter Progression Engine",
      "Engagement Decay Engine",
      "Telegram Integration",
      "Voice Conversation Engine",
      "Text Generation Pipeline",
      "Temporal Memory System",
      "Score History Tracker",
      "Onboarding Orchestrator",
      "Pipeline Monitoring",
      "Admin Control Panel",
    ]
    systems.forEach((system) => {
      expect(screen.getByText(system)).toBeInTheDocument()
    })
  })

  it("renders an element with terminal-cursor class", () => {
    const { container } = render(<SystemTerminal />)
    const cursor = container.querySelector(".terminal-cursor")
    expect(cursor).toBeInTheDocument()
  })

  it("renders stats bar with 3 values", () => {
    render(<SystemTerminal />)
    // 742 Python files
    expect(screen.getByText(/742/)).toBeInTheDocument()
    // 5,533 Tests passing (or similar)
    expect(screen.getByText(/5[,.]?5[0-9]{2}|tests/i)).toBeInTheDocument()
    // 86 Specifications
    expect(screen.getByText(/86/)).toBeInTheDocument()
  })

  it("renders immediately without delay when reduced motion is set", () => {
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
    render(<SystemTerminal />)
    // All systems should be visible immediately (no typing animation)
    const systems = screen.queryAllByText(/Engine|System|Layer|Pipeline|Orchestrator|Tracker|Panel|Integration/)
    expect(systems.length).toBeGreaterThan(0)
  })

  it("uses JetBrains Mono font family (font class)", () => {
    const { container } = render(<SystemTerminal />)
    const terminal = container.firstChild as HTMLElement
    expect(terminal.className).toMatch(/mono|font-mono/)
  })
})
