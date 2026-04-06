/**
 * Tests for useSocialCircle hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { SocialCircleResponse } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getSocialCircle: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useSocialCircle } from "@/hooks/use-social-circle"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockSocialCircle: SocialCircleResponse = {
  friends: [
    {
      id: "f-1",
      friend_name: "Sarah",
      friend_role: "bestie",
      age: 24,
      occupation: "nurse",
      personality: "bubbly and supportive",
      relationship_to_nikita: "childhood friend",
      storyline_potential: ["wingwoman", "gossip"],
      is_active: true,
    },
    {
      id: "f-2",
      friend_name: "Marcus",
      friend_role: "ex",
      age: 28,
      occupation: null,
      personality: null,
      relationship_to_nikita: "ex-boyfriend",
      storyline_potential: ["jealousy_trigger"],
      is_active: true,
    },
  ],
  total_count: 2,
}

describe("useSocialCircle", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getSocialCircle).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useSocialCircle(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("returns social circle data on success", async () => {
    vi.mocked(portalApi.getSocialCircle).mockResolvedValue(mockSocialCircle)

    const { result } = renderHook(() => useSocialCircle(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.friends).toHaveLength(2)
    expect(result.current.data?.friends[0].friend_name).toBe("Sarah")
    expect(result.current.data?.total_count).toBe(2)
  })

  it("uses correct query key ['portal', 'social-circle']", async () => {
    vi.mocked(portalApi.getSocialCircle).mockResolvedValue(mockSocialCircle)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useSocialCircle(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "social-circle"])
    expect(cached).toEqual(mockSocialCircle)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getSocialCircle).mockRejectedValue({ detail: "Forbidden", status: 403 })

    const { result } = renderHook(() => useSocialCircle(), { wrapper })

    await waitFor(() => expect(portalApi.getSocialCircle).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
