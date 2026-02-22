/**
 * Tests for LoadingSkeleton component
 */
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"

describe("LoadingSkeleton", () => {
  it("renders ring variant with circular skeleton", () => {
    const { container } = render(<LoadingSkeleton variant="ring" />)
    // The ring variant wraps in a flex col with items-center
    const wrapper = container.querySelector(".flex-col")
    expect(wrapper).toBeInTheDocument()
    // Has a rounded-full element (the ring circle)
    const circle = container.querySelector(".rounded-full")
    expect(circle).toBeInTheDocument()
  })

  it("renders chart variant", () => {
    const { container } = render(<LoadingSkeleton variant="chart" />)
    const skeleton = container.querySelector(".h-\\[280px\\]")
    expect(skeleton).toBeInTheDocument()
  })

  it("renders card-grid variant with default 3 cards", () => {
    const { container } = render(<LoadingSkeleton variant="card-grid" />)
    const cards = container.querySelectorAll(".h-\\[140px\\]")
    expect(cards).toHaveLength(3)
  })

  it("renders card-grid variant with custom count", () => {
    const { container } = render(<LoadingSkeleton variant="card-grid" count={5} />)
    const cards = container.querySelectorAll(".h-\\[140px\\]")
    expect(cards).toHaveLength(5)
  })

  it("renders table variant with header + default 3 rows", () => {
    const { container } = render(<LoadingSkeleton variant="table" />)
    // Header h-10 + 3 rows h-12 = 4 skeletons total
    const headerRow = container.querySelector(".h-10")
    expect(headerRow).toBeInTheDocument()
    const dataRows = container.querySelectorAll(".h-12")
    expect(dataRows).toHaveLength(3)
  })

  it("renders kpi variant", () => {
    const { container } = render(<LoadingSkeleton variant="kpi" />)
    const kpi = container.querySelector(".h-9")
    expect(kpi).toBeInTheDocument()
  })

  it("renders card variant", () => {
    const { container } = render(<LoadingSkeleton variant="card" />)
    const card = container.querySelector(".h-20")
    expect(card).toBeInTheDocument()
  })

  it("applies custom className", () => {
    const { container } = render(
      <LoadingSkeleton variant="chart" className="custom-test-class" />
    )
    const el = container.querySelector(".custom-test-class")
    expect(el).toBeInTheDocument()
  })
})
