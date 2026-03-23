/**
 * Tests for ScoreRing component
 * Verifies decimal precision is preserved (GH #150)
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScoreRing } from "@/components/charts/score-ring"

// Mock framer-motion to avoid animation issues in jsdom
vi.mock("framer-motion", () => ({
  motion: {
    circle: ({ children, ...props }: React.SVGProps<SVGCircleElement>) =>
      <circle {...props}>{children}</circle>,
    span: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) =>
      <span {...props}>{children}</span>,
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) =>
      <div {...props}>{children}</div>,
  },
}))

describe("ScoreRing", () => {
  it("renders integer score without trailing decimal", () => {
    render(<ScoreRing score={75} />)
    expect(screen.getByText("75")).toBeInTheDocument()
  })

  it("preserves one decimal place for fractional scores", () => {
    render(<ScoreRing score={75.4} />)
    expect(screen.getByText("75.4")).toBeInTheDocument()
  })

  it("rounds to one decimal place", () => {
    render(<ScoreRing score={62.37} />)
    expect(screen.getByText("62.4")).toBeInTheDocument()
  })

  it("sets aria-label with decimal precision", () => {
    render(<ScoreRing score={75.4} />)
    expect(screen.getByRole("meter")).toHaveAttribute(
      "aria-label",
      "Relationship score: 75.4"
    )
  })

  it("sets aria-label without trailing zero for integers", () => {
    render(<ScoreRing score={80} />)
    expect(screen.getByRole("meter")).toHaveAttribute(
      "aria-label",
      "Relationship score: 80"
    )
  })

  it("renders with correct meter role and value attributes", () => {
    render(<ScoreRing score={55.5} />)
    const meter = screen.getByRole("meter")
    expect(meter).toHaveAttribute("aria-valuenow", "55.5")
    expect(meter).toHaveAttribute("aria-valuemin", "0")
    expect(meter).toHaveAttribute("aria-valuemax", "100")
  })
})
