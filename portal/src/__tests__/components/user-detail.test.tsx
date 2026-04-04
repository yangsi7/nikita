/**
 * Tests for UserDetail component
 * Verifies user data fields: phone/id, chapter, score, days played, boss attempts
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { UserDetail } from "@/components/admin/user-detail"
import type { AdminUserDetail } from "@/lib/api/types"

const mockUser: AdminUserDetail = {
  id: "abc12345-6789-0000-1111-222233334444",
  telegram_id: 12345678,
  phone: "+1234567890",
  relationship_score: 72.5,
  chapter: 3,
  boss_attempts: 2,
  days_played: 14,
  game_status: "active",
  last_interaction_at: "2026-03-20T15:00:00Z",
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-20T15:00:00Z",
}

describe("UserDetail", () => {
  it("renders phone number as heading when available", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("+1234567890")).toBeInTheDocument()
  })

  it("renders telegram ID when phone is null", () => {
    const noPhone: AdminUserDetail = { ...mockUser, phone: null }
    render(<UserDetail user={noPhone} />)
    expect(screen.getByText("TG: 12345678")).toBeInTheDocument()
  })

  it("renders truncated ID when both phone and telegram_id are null", () => {
    const noIdentifiers: AdminUserDetail = { ...mockUser, phone: null, telegram_id: null }
    render(<UserDetail user={noIdentifiers} />)
    expect(screen.getByText("abc12345-678")).toBeInTheDocument()
  })

  it("renders chapter with roman numeral", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("Chapter III")).toBeInTheDocument()
  })

  it("renders game status badge", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("active")).toBeInTheDocument()
  })

  it("renders rounded relationship score", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("73")).toBeInTheDocument()
  })

  it("renders days played", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("14")).toBeInTheDocument()
  })

  it("renders boss attempts", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("2")).toBeInTheDocument()
  })

  it("renders stat labels", () => {
    render(<UserDetail user={mockUser} />)
    expect(screen.getByText("Score")).toBeInTheDocument()
    expect(screen.getByText("Days Played")).toBeInTheDocument()
    expect(screen.getByText("Boss Attempts")).toBeInTheDocument()
    expect(screen.getByText("Last Active")).toBeInTheDocument()
  })

  it("renders 'Never' when last_interaction_at is null", () => {
    const noInteraction: AdminUserDetail = { ...mockUser, last_interaction_at: null }
    render(<UserDetail user={noInteraction} />)
    expect(screen.getByText("Never")).toBeInTheDocument()
  })
})
