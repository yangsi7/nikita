/**
 * Tests for ConflictBanner component
 * Verifies conditional rendering based on conflict_state and content display
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConflictBanner } from "@/components/dashboard/conflict-banner"

describe("ConflictBanner", () => {
  it("returns null when conflict_state is 'none'", () => {
    const { container } = render(
      <ConflictBanner conflictState="none" />
    )
    expect(container.innerHTML).toBe("")
  })

  it("renders alert banner for 'cold' conflict", () => {
    render(
      <ConflictBanner
        conflictState="cold"
        conflictTrigger="ignored messages"
        conflictStartedAt="2026-03-20T14:00:00Z"
      />
    )
    expect(screen.getByRole("alert")).toBeInTheDocument()
    expect(screen.getByText("Nikita went cold")).toBeInTheDocument()
    expect(screen.getByText("cold")).toBeInTheDocument()
    expect(screen.getByText("ignored messages")).toBeInTheDocument()
  })

  it("renders narrative text for 'passive_aggressive'", () => {
    render(
      <ConflictBanner conflictState="passive_aggressive" />
    )
    expect(screen.getByText("Nikita is being passive-aggressive")).toBeInTheDocument()
    expect(screen.getByText("passive aggressive")).toBeInTheDocument()
  })

  it("renders narrative text for 'explosive'", () => {
    render(
      <ConflictBanner conflictState="explosive" />
    )
    expect(screen.getByText("Nikita is furious")).toBeInTheDocument()
  })

  it("renders fallback text for unknown conflict state", () => {
    render(
      <ConflictBanner conflictState="unknown_state" />
    )
    expect(screen.getByText("Nikita is upset")).toBeInTheDocument()
  })

  it("does not render trigger text when conflictTrigger is null", () => {
    render(
      <ConflictBanner conflictState="cold" conflictTrigger={null} />
    )
    expect(screen.getByText("Nikita went cold")).toBeInTheDocument()
    // Should not have a trigger paragraph
    expect(screen.queryByText("ignored messages")).not.toBeInTheDocument()
  })
})
