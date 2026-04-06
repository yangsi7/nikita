/**
 * Tests for FriendCard component
 * Verifies name, role, avatar fallback initials, optional fields
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FriendCard } from "@/components/dashboard/friend-card"
import type { SocialCircleMember } from "@/lib/api/types"

const mockFriend: SocialCircleMember = {
  id: "f1",
  friend_name: "Mila Petrova",
  friend_role: "Best friend",
  age: 24,
  occupation: "Photographer",
  personality: "Wild and spontaneous",
  relationship_to_nikita: "Childhood best friend",
  storyline_potential: ["jealousy", "adventure"],
  is_active: true,
}

describe("FriendCard", () => {
  it("renders friend name", () => {
    render(<FriendCard friend={mockFriend} />)
    expect(screen.getByText("Mila Petrova")).toBeInTheDocument()
  })

  it("renders friend role", () => {
    render(<FriendCard friend={mockFriend} />)
    expect(screen.getByText("Best friend")).toBeInTheDocument()
  })

  it("renders avatar fallback with initials", () => {
    render(<FriendCard friend={mockFriend} />)
    // Initials: "M" + "P" = "MP"
    expect(screen.getByText("MP")).toBeInTheDocument()
  })

  it("renders occupation when provided", () => {
    render(<FriendCard friend={mockFriend} />)
    expect(screen.getByText("Photographer")).toBeInTheDocument()
  })

  it("renders personality when provided", () => {
    render(<FriendCard friend={mockFriend} />)
    expect(screen.getByText("Wild and spontaneous")).toBeInTheDocument()
  })

  it("renders relationship to Nikita", () => {
    render(<FriendCard friend={mockFriend} />)
    expect(screen.getByText("Childhood best friend")).toBeInTheDocument()
  })

  it("renders storyline potential badges", () => {
    render(<FriendCard friend={mockFriend} />)
    expect(screen.getByText("jealousy")).toBeInTheDocument()
    expect(screen.getByText("adventure")).toBeInTheDocument()
  })

  it("omits optional fields when null", () => {
    const minimal: SocialCircleMember = {
      ...mockFriend,
      occupation: null,
      personality: null,
      relationship_to_nikita: null,
      storyline_potential: [],
    }
    render(<FriendCard friend={minimal} />)
    expect(screen.getByText("Mila Petrova")).toBeInTheDocument()
    expect(screen.queryByText("Photographer")).not.toBeInTheDocument()
    expect(screen.queryByText("Wild and spontaneous")).not.toBeInTheDocument()
  })

  it("renders single-name friend initials correctly", () => {
    const singleName: SocialCircleMember = {
      ...mockFriend,
      friend_name: "Natasha",
    }
    render(<FriendCard friend={singleName} />)
    expect(screen.getByText("N")).toBeInTheDocument()
  })
})
