/**
 * Tests for useAdminUser and useAdminUserPipelineHistory hooks
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { AdminUserDetail } from "@/lib/api/types"

vi.mock("@/lib/api/admin", () => ({
  adminApi: {
    getUser: vi.fn(),
    getPipelineHistory: vi.fn(),
  },
}))

import { adminApi } from "@/lib/api/admin"
import { useAdminUser, useAdminUserPipelineHistory } from "@/hooks/use-admin-user"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockAdminUserDetail: AdminUserDetail = {
  id: "user-detail-1",
  telegram_id: 123456789,
  phone: "+41445056044",
  relationship_score: 72,
  chapter: 3,
  boss_attempts: 1,
  days_played: 21,
  game_status: "active",
  last_interaction_at: "2026-03-20T14:00:00Z",
  created_at: "2026-02-28T10:00:00Z",
  updated_at: "2026-03-20T14:00:00Z",
}

describe("useAdminUser", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches correct user by ID", async () => {
    vi.mocked(adminApi.getUser).mockResolvedValue(mockAdminUserDetail)

    const { result } = renderHook(() => useAdminUser("user-detail-1"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(adminApi.getUser).toHaveBeenCalledWith("user-detail-1")
    expect(result.current.data?.relationship_score).toBe(72)
  })

  it("returns isLoading then isSuccess states", async () => {
    vi.mocked(adminApi.getUser).mockResolvedValue(mockAdminUserDetail)

    const { result } = renderHook(() => useAdminUser("user-detail-1"), { wrapper })

    // Initially loading
    expect(result.current.isLoading).toBe(true)
    expect(result.current.isSuccess).toBe(false)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.isLoading).toBe(false)
  })

  it("uses correct query key ['admin', 'user', id]", async () => {
    vi.mocked(adminApi.getUser).mockResolvedValue(mockAdminUserDetail)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useAdminUser("user-detail-1"), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["admin", "user", "user-detail-1"])
    expect(cached).toEqual(mockAdminUserDetail)
  })

  it("is disabled when id is empty", async () => {
    const { result } = renderHook(() => useAdminUser(""), { wrapper })

    expect(result.current.fetchStatus).toBe("idle")
    expect(adminApi.getUser).not.toHaveBeenCalled()
  })
})

describe("useAdminUserPipelineHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches pipeline history for a user", async () => {
    const mockHistory = { items: [], total_count: 0, page: 1, page_size: 20 }
    vi.mocked(adminApi.getPipelineHistory).mockResolvedValue(mockHistory)

    const { result } = renderHook(() => useAdminUserPipelineHistory("user-detail-1"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(adminApi.getPipelineHistory).toHaveBeenCalledWith("user-detail-1")
    expect(result.current.data).toEqual(mockHistory)
  })
})
