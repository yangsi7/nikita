/**
 * Tests for LoadingSkeleton component
 */
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"

describe("LoadingSkeleton", () => {
  it("renders ring variant with circular skeleton", () => {
    const { container } = render(<LoadingSkeleton variant="ring" />)
    // Component generates data-testid="skeleton-ring" automatically
    const wrapper = container.querySelector('[data-testid="skeleton-ring"]')
    expect(wrapper).toBeInTheDocument()
    // Has a rounded-full element (the ring circle)
    const circle = container.querySelector(".rounded-full")
    expect(circle).toBeInTheDocument()
  })

  it("renders chart variant", () => {
    const { container } = render(<LoadingSkeleton variant="chart" />)
    const skeleton = container.querySelector('[data-testid="skeleton-chart"]')
    expect(skeleton).toBeInTheDocument()
  })

  it("renders card-grid variant with default 3 cards", () => {
    const { container } = render(<LoadingSkeleton variant="card-grid" />)
    const grid = container.querySelector('[data-testid="skeleton-card-grid"]')
    expect(grid).toBeInTheDocument()
    // Default count=3 → 3 skeleton children
    const cards = grid!.children
    expect(cards).toHaveLength(3)
  })

  it("renders card-grid variant with custom count", () => {
    const { container } = render(<LoadingSkeleton variant="card-grid" count={5} />)
    const grid = container.querySelector('[data-testid="skeleton-card-grid"]')
    expect(grid).toBeInTheDocument()
    const cards = grid!.children
    expect(cards).toHaveLength(5)
  })

  it("renders table variant with header + default 3 rows", () => {
    const { container } = render(<LoadingSkeleton variant="table" />)
    const table = container.querySelector('[data-testid="skeleton-table"]')
    expect(table).toBeInTheDocument()
    // Header (1) + 3 data rows = 4 children
    const rows = table!.children
    expect(rows).toHaveLength(4)
  })

  it("renders kpi variant", () => {
    const { container } = render(<LoadingSkeleton variant="kpi" />)
    const kpi = container.querySelector('[data-testid="skeleton-kpi"]')
    expect(kpi).toBeInTheDocument()
  })

  it("renders card variant", () => {
    const { container } = render(<LoadingSkeleton variant="card" />)
    const card = container.querySelector('[data-testid="skeleton-card"]')
    expect(card).toBeInTheDocument()
  })

  it("applies custom className", () => {
    const { container } = render(
      <LoadingSkeleton variant="chart" className="custom-test-class" />
    )
    const el = container.querySelector('[data-testid="skeleton-chart"]')
    expect(el).toBeInTheDocument()
    expect(el!.className).toContain("custom-test-class")
  })
})
