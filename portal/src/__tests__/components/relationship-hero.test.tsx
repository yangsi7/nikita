/**
 * Tests for RelationshipHero component
 * Tests rendering with various UserStats configurations
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { RelationshipHero } from "@/components/dashboard/relationship-hero"
import { createMockUser } from "../utils/test-utils"
import type { UserStats } from "@/lib/api/types"

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
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe("RelationshipHero", () => {
  it("renders relationship score", () => {
    const stats = createMockUser()
    render(<RelationshipHero stats={stats} />)
    // ScoreRing renders the score as a number
    expect(screen.getByText("62")).toBeInTheDocument()
  })

  it("renders chapter name badge", () => {
    const stats = createMockUser()
    render(<RelationshipHero stats={stats} />)
    expect(screen.getByText(/Getting Closer/)).toBeInTheDocument()
  })

  it("renders chapter roman numeral", () => {
    const stats = createMockUser()
    render(<RelationshipHero stats={stats} />)
    expect(screen.getByText(/Chapter II/)).toBeInTheDocument()
  })

  it("renders game status badge", () => {
    const stats = createMockUser()
    render(<RelationshipHero stats={stats} />)
    expect(screen.getByText("active")).toBeInTheDocument()
  })

  it("renders days played", () => {
    const stats = createMockUser()
    render(<RelationshipHero stats={stats} />)
    expect(screen.getByText(/14 days played/)).toBeInTheDocument()
  })

  it("shows boss attempts when > 0", () => {
    const stats: UserStats = { ...createMockUser(), boss_attempts: 2 }
    render(<RelationshipHero stats={stats} />)
    expect(screen.getByText(/2 boss attempts/)).toBeInTheDocument()
  })

  it("hides boss progress when not in boss_fight status", () => {
    const stats = createMockUser() // game_status: "active"
    render(<RelationshipHero stats={stats} />)
    expect(screen.queryByText(/Boss Progress/)).not.toBeInTheDocument()
  })

  it("shows boss progress bar when in boss_fight status", () => {
    const stats: UserStats = {
      ...createMockUser(),
      game_status: "boss_fight",
      progress_to_boss: 67,
    }
    render(<RelationshipHero stats={stats} />)
    expect(screen.getByText("Boss Progress")).toBeInTheDocument()
    expect(screen.getByText("67%")).toBeInTheDocument()
  })
})
