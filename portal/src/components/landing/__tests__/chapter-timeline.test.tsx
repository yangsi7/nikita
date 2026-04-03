import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ChapterTimeline } from "../chapter-timeline"

describe("ChapterTimeline — T019 AC-REQ-012", () => {
  it("renders exactly 5 chapter dots", () => {
    const { container } = render(<ChapterTimeline />)
    const dots = container.querySelectorAll("[data-testid='chapter-dot']")
    expect(dots).toHaveLength(5)
  })

  it("renders all 5 chapter names — spec marketing names", () => {
    render(<ChapterTimeline />)
    // Marketing names (Spark=Curiosity, Home=Established per spec comment)
    expect(screen.getByText(/spark/i)).toBeInTheDocument()
    expect(screen.getByText(/intrigue/i)).toBeInTheDocument()
    expect(screen.getByText(/investment/i)).toBeInTheDocument()
    expect(screen.getByText(/intimacy/i)).toBeInTheDocument()
    expect(screen.getByText(/home/i)).toBeInTheDocument()
  })

  it("renders all 5 chapter thresholds from config (55-75%)", () => {
    render(<ChapterTimeline />)
    // Authoritative: config_data/chapters.yaml (not constitution §3.2 which is stale)
    expect(screen.getByText(/55%/)).toBeInTheDocument()
    expect(screen.getByText(/60%/)).toBeInTheDocument()
    expect(screen.getByText(/65%/)).toBeInTheDocument()
    expect(screen.getByText(/70%/)).toBeInTheDocument()
    expect(screen.getByText(/75%/)).toBeInTheDocument()
  })

  it("renders Ch1–Ch5 labels", () => {
    render(<ChapterTimeline />)
    expect(screen.getByText(/ch1|chapter 1/i)).toBeInTheDocument()
    expect(screen.getByText(/ch5|chapter 5/i)).toBeInTheDocument()
  })

  it("has overflow-x-auto for mobile scrolling", () => {
    const { container } = render(<ChapterTimeline />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toMatch(/overflow-x-auto/)
  })
})
