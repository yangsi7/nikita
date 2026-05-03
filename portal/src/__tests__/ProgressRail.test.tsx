import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { ProgressRail } from "@/app/onboarding/_components/ProgressRail"

describe("ProgressRail — AC C1.8 / C1.17", () => {
  it("renders a progressbar role with current value", () => {
    render(<ProgressRail progressPct={42} />)
    const bar = screen.getByRole("progressbar", { name: /onboarding progress/i })
    expect(bar).toHaveAttribute("aria-valuenow", "42")
    expect(bar).toHaveAttribute("aria-valuemin", "0")
    expect(bar).toHaveAttribute("aria-valuemax", "100")
  })

  it("clamps progress into [0,100]", () => {
    const { rerender } = render(<ProgressRail progressPct={-5} />)
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0")
    rerender(<ProgressRail progressPct={150} />)
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100")
  })

  it("renders progress at 0 with 0%", () => {
    render(<ProgressRail progressPct={0} />)
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0")
  })

  it("rounds non-integer progress to nearest int", () => {
    render(<ProgressRail progressPct={73.6} />)
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "74")
  })
})
