/**
 * Spec 214 T3.8 — ProgressHeader tests.
 *
 * ACs:
 *   - AC-T3.8.1: width maps to progress_pct; label text format matches
 *   - AC-T3.8.2: client renders server pct verbatim (no re-derivation)
 */

import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"

import { ProgressHeader } from "../components/ProgressHeader"

describe("ProgressHeader — AC-T3.8.1", () => {
  it("renders 'Building your file... N%' label with server pct", () => {
    render(<ProgressHeader progressPct={42} />)
    expect(screen.getByTestId("progress-label").textContent).toBe(
      "Building your file... 42%"
    )
  })

  it("sets width style to {pct}%", () => {
    render(<ProgressHeader progressPct={42} />)
    const bar = screen.getByTestId("progress-bar")
    expect(bar.getAttribute("style")).toContain("width: 42%")
  })

  it("clamps values above 100", () => {
    render(<ProgressHeader progressPct={150} />)
    expect(screen.getByTestId("progress-label").textContent).toBe(
      "Building your file... 100%"
    )
  })

  it("clamps negative values to 0", () => {
    render(<ProgressHeader progressPct={-5} />)
    expect(screen.getByTestId("progress-label").textContent).toBe(
      "Building your file... 0%"
    )
  })
})

describe("ProgressHeader — AC-T3.8.2 server-owned math", () => {
  it("does not derive; mocked 42 renders 42%", () => {
    render(<ProgressHeader progressPct={42} />)
    expect(screen.getByTestId("progress-label").textContent).toContain("42%")
  })
})
