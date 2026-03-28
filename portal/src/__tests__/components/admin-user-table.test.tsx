/**
 * Tests for UserTable component
 * Verifies table render, search input, and filter elements
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { AdminUser } from "@/lib/api/types"

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    refresh: vi.fn(),
  }),
}))

const mockUsers: AdminUser[] = [
  {
    id: "user-1",
    telegram_id: "111222333",
    email: "alice@example.com",
    relationship_score: 72,
    chapter: 3,
    engagement_state: "in_zone",
    game_status: "active",
    last_interaction_at: "2026-03-20T14:00:00Z",
    created_at: "2026-02-01T10:00:00Z",
  },
  {
    id: "user-2",
    telegram_id: null,
    email: "bob@example.com",
    relationship_score: 45,
    chapter: 1,
    engagement_state: "calibrating",
    game_status: "active",
    last_interaction_at: null,
    created_at: "2026-03-15T08:00:00Z",
  },
]

// Mock the useAdminUsers hook
vi.mock("@/hooks/use-admin-users", () => ({
  useAdminUsers: vi.fn(),
}))

import { useAdminUsers } from "@/hooks/use-admin-users"
import { UserTable } from "@/components/admin/user-table"

function renderWithProviders(ui: React.ReactElement) {
  const qc = createTestQueryClient()
  return render(
    <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
  )
}

describe("UserTable", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders table with user data", () => {
    vi.mocked(useAdminUsers).mockReturnValue({
      data: mockUsers,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAdminUsers>)

    renderWithProviders(<UserTable />)

    expect(screen.getByText("alice@example.com")).toBeInTheDocument()
    expect(screen.getByText("bob@example.com")).toBeInTheDocument()
    expect(screen.getByText("72")).toBeInTheDocument()
    expect(screen.getByText("45")).toBeInTheDocument()
  })

  it("renders search input with placeholder", () => {
    vi.mocked(useAdminUsers).mockReturnValue({
      data: mockUsers,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAdminUsers>)

    renderWithProviders(<UserTable />)

    const searchInput = screen.getByPlaceholderText(/search by name, email, telegram id/i)
    expect(searchInput).toBeInTheDocument()
  })

  it("renders chapter and engagement filter selects", () => {
    vi.mocked(useAdminUsers).mockReturnValue({
      data: mockUsers,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAdminUsers>)

    renderWithProviders(<UserTable />)

    // Chapter filter trigger shows "All Chapters" by default
    expect(screen.getByText("All Chapters")).toBeInTheDocument()
    // Engagement filter trigger shows "All States" by default
    expect(screen.getByText("All States")).toBeInTheDocument()
  })

  it("shows table headers", () => {
    vi.mocked(useAdminUsers).mockReturnValue({
      data: mockUsers,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAdminUsers>)

    renderWithProviders(<UserTable />)

    expect(screen.getByText("User")).toBeInTheDocument()
    expect(screen.getByText("Score")).toBeInTheDocument()
    expect(screen.getByText("Chapter")).toBeInTheDocument()
    expect(screen.getByText("Engagement")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("Last Active")).toBeInTheDocument()
  })

  it("shows empty state when no users", () => {
    vi.mocked(useAdminUsers).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAdminUsers>)

    renderWithProviders(<UserTable />)

    expect(screen.getByText("No users found")).toBeInTheDocument()
  })

  it("displays telegram ID for user with telegram", () => {
    vi.mocked(useAdminUsers).mockReturnValue({
      data: mockUsers,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAdminUsers>)

    renderWithProviders(<UserTable />)

    expect(screen.getByText("TG: 111222333")).toBeInTheDocument()
  })
})
