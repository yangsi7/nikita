/**
 * Tests for DiaryEntry component
 * Verifies summary text, date, score delta badge, conversations count
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { DiaryEntry } from "@/components/dashboard/diary-entry"
import type { DailySummary } from "@/lib/api/types"

const mockSummary: DailySummary = {
  id: "ds-1",
  date: "2026-03-20",
  score_start: 60,
  score_end: 65.5,
  decay_applied: -0.3,
  conversations_count: 3,
  summary_text: "A heartfelt conversation about childhood memories",
  emotional_tone: "positive",
}

describe("DiaryEntry", () => {
  it("renders summary text in quotes", () => {
    render(<DiaryEntry summary={mockSummary} />)
    expect(
      screen.getByText(/A heartfelt conversation about childhood memories/)
    ).toBeInTheDocument()
  })

  it("renders formatted date", () => {
    render(<DiaryEntry summary={mockSummary} />)
    // formatDate produces "Mar 20, 2026" or similar
    expect(screen.getByText(/Mar 20/)).toBeInTheDocument()
  })

  it("renders positive score delta with + prefix", () => {
    render(<DiaryEntry summary={mockSummary} />)
    // delta = 65.5 - 60 = 5.5
    expect(screen.getByText("+5.5")).toBeInTheDocument()
  })

  it("renders negative score delta", () => {
    const negative: DailySummary = {
      ...mockSummary,
      score_start: 70,
      score_end: 66,
    }
    render(<DiaryEntry summary={negative} />)
    expect(screen.getByText("-4.0")).toBeInTheDocument()
  })

  it("renders conversations count", () => {
    render(<DiaryEntry summary={mockSummary} />)
    expect(screen.getByText("3 chats")).toBeInTheDocument()
  })

  it("renders fallback when summary_text is null", () => {
    const noSummary: DailySummary = { ...mockSummary, summary_text: null }
    render(<DiaryEntry summary={noSummary} />)
    expect(screen.getByText(/No summary available/)).toBeInTheDocument()
  })

  it("renders data-testid on card", () => {
    render(<DiaryEntry summary={mockSummary} />)
    expect(screen.getByTestId("card-diary-ds-1")).toBeInTheDocument()
  })
})
