/**
 * Tests for sidebar player name display
 * Verifies user_profiles.name is shown instead of hardcoded "Player"
 * GH #641
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AppLayout } from "@/components/layout/sidebar"
import { usePlayerName } from "@/hooks/use-player-name"

vi.mock("@/hooks/use-player-name", () => ({
  usePlayerName: vi.fn(() => "Sam"),
}))

// Stub Next.js router hooks used by sidebar
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

// Stub createClient (used in sidebar for logout)
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { signOut: vi.fn() },
  }),
}))

// Stub NotificationCenter to avoid its internal hooks
vi.mock("@/components/notifications/notification-center", () => ({
  NotificationCenter: () => null,
}))

// Stub MobileNav to avoid its internal hooks
vi.mock("@/components/layout/mobile-nav", () => ({
  MobileNav: () => null,
}))

describe("AppLayout sidebar player name", () => {
  it("renders user profile name instead of hardcoded Player", () => {
    vi.mocked(usePlayerName).mockReturnValue("Sam")
    render(<AppLayout variant="player"><div /></AppLayout>)
    expect(screen.getByText("Sam")).toBeInTheDocument()
    expect(screen.queryByText("Player")).not.toBeInTheDocument()
  })

  it("renders fallback You when usePlayerName returns You", () => {
    vi.mocked(usePlayerName).mockReturnValue("You")
    render(<AppLayout variant="player"><div /></AppLayout>)
    expect(screen.getByText("You")).toBeInTheDocument()
    expect(screen.queryByText("Player")).not.toBeInTheDocument()
  })
})
