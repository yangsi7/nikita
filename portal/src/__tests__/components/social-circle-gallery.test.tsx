/**
 * Tests for SocialCircleGallery component
 * Verifies friend card list, count header, and empty state
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SocialCircleGallery } from "@/components/dashboard/social-circle-gallery"
import type { SocialCircleMember } from "@/lib/api/types"

const mockFriends: SocialCircleMember[] = [
  {
    id: "f1",
    friend_name: "Mila Petrova",
    friend_role: "Best friend",
    age: 24,
    occupation: "Photographer",
    personality: "Wild and spontaneous",
    relationship_to_nikita: "Childhood best friend",
    storyline_potential: ["jealousy", "adventure"],
    is_active: true,
  },
  {
    id: "f2",
    friend_name: "Dasha Kim",
    friend_role: "Work colleague",
    age: 27,
    occupation: "Designer",
    personality: null,
    relationship_to_nikita: null,
    storyline_potential: [],
    is_active: true,
  },
]

describe("SocialCircleGallery", () => {
  it("renders empty state when no friends", () => {
    render(<SocialCircleGallery friends={[]} />)
    expect(screen.getByText(/hasn.t mentioned her friends/i)).toBeInTheDocument()
  })

  it("renders count header matching array length", () => {
    render(<SocialCircleGallery friends={mockFriends} />)
    expect(screen.getByText("2 Friends")).toBeInTheDocument()
  })

  it("renders singular 'Friend' for single friend", () => {
    render(<SocialCircleGallery friends={[mockFriends[0]]} />)
    expect(screen.getByText("1 Friend")).toBeInTheDocument()
  })

  it("renders friend names in cards", () => {
    render(<SocialCircleGallery friends={mockFriends} />)
    expect(screen.getByText("Mila Petrova")).toBeInTheDocument()
    expect(screen.getByText("Dasha Kim")).toBeInTheDocument()
  })

  it("renders friend roles", () => {
    render(<SocialCircleGallery friends={mockFriends} />)
    expect(screen.getByText("Best friend")).toBeInTheDocument()
    expect(screen.getByText("Work colleague")).toBeInTheDocument()
  })
})
