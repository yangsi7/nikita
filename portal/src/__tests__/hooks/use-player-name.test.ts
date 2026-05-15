/**
 * Tests for usePlayerName hook
 * Covers success, error (RLS reject / network fail), and no-user paths
 * GH #641
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"

// Must mock before importing the hook
vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}))

import { createClient } from "@/lib/supabase/client"
import { usePlayerName } from "@/hooks/use-player-name"

function wrapper({ children }: { children: React.ReactNode }) {
  // createTestQueryClient sets retry: false at QueryClient level, but usePlayerName
  // sets retry: 1 at query level — query-level wins per React Query precedence.
  // Tests that mock rejected queryFn will retry once before settling to isError.
  // Use waitFor() with a generous timeout to accommodate that single retry.
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

function mockSupabase({
  user = { id: "user-1", email: "sam@example.com" },
  profileData = null as { name: string } | null,
  profileError = null as { message: string } | null,
} = {}) {
  const singleFn = vi.fn().mockResolvedValue({ data: profileData, error: profileError })
  const eqFn = vi.fn(() => ({ single: singleFn }))
  const selectFn = vi.fn(() => ({ eq: eqFn }))
  const fromFn = vi.fn(() => ({ select: selectFn }))

  vi.mocked(createClient).mockReturnValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user } }),
    },
    from: fromFn,
  } as unknown as ReturnType<typeof createClient>)
}

describe("usePlayerName", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns profile name when user_profiles.name is set", async () => {
    mockSupabase({ profileData: { name: "Postmerge" } })
    const { result } = renderHook(() => usePlayerName(), { wrapper })
    await waitFor(() => expect(result.current).toBe("Postmerge"))
  })

  it("falls back to email username when profile has no name", async () => {
    mockSupabase({ profileData: null, profileError: null })
    const { result } = renderHook(() => usePlayerName(), { wrapper })
    await waitFor(() => expect(result.current).toBe("sam"))
  })

  it("returns You when no user is authenticated", async () => {
    vi.mocked(createClient).mockReturnValue({
      auth: {
        getUser: vi.fn().mockResolvedValue({ data: { user: null } }),
      },
      from: vi.fn(),
    } as unknown as ReturnType<typeof createClient>)

    const { result } = renderHook(() => usePlayerName(), { wrapper })
    await waitFor(() => expect(result.current).toBe("You"))
  })

  it("falls back to email username on RLS error (profile error is non-fatal)", async () => {
    mockSupabase({
      profileData: null,
      profileError: { message: "new row violates row-level security policy" },
    })
    const { result } = renderHook(() => usePlayerName(), { wrapper })
    // Email fallback still fires — profile error is non-fatal
    await waitFor(() => expect(result.current).toBe("sam"))
  })

  it("returns You when both profile and email are unavailable", async () => {
    vi.mocked(createClient).mockReturnValue({
      auth: {
        getUser: vi.fn().mockResolvedValue({
          data: { user: { id: "user-1", email: undefined } },
        }),
      },
      from: vi.fn(() => ({
        select: vi.fn(() => ({
          eq: vi.fn(() => ({
            single: vi.fn().mockResolvedValue({ data: null, error: { message: "RLS" } }),
          })),
        })),
      })),
    } as unknown as ReturnType<typeof createClient>)

    const { result } = renderHook(() => usePlayerName(), { wrapper })
    await waitFor(() => expect(result.current).toBe("You"))
  })
})
