/**
 * Tests for useAdminStats hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { AdminStats } from "@/lib/api/types"

vi.mock("@/lib/api/admin", () => ({
  adminApi: {
    getStats: vi.fn(),
  },
}))

import { adminApi } from "@/lib/api/admin"
import { useAdminStats } from "@/hooks/use-admin-stats"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockAdminStats: AdminStats = {
  total_users: 100,
  active_users: 42,
  new_users_7d: 8,
  total_conversations: 1500,
  avg_relationship_score: 58.5,
}

describe("useAdminStats", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns admin stats on success", async () => {
    vi.mocked(adminApi.getStats).mockResolvedValue(mockAdminStats)

    const { result } = renderHook(() => useAdminStats(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockAdminStats)
  })

  it("exposes total_users and active_users", async () => {
    vi.mocked(adminApi.getStats).mockResolvedValue(mockAdminStats)

    const { result } = renderHook(() => useAdminStats(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_users).toBe(100)
    expect(result.current.data?.active_users).toBe(42)
  })

  it("uses correct query key ['admin', 'stats']", async () => {
    vi.mocked(adminApi.getStats).mockResolvedValue(mockAdminStats)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useAdminStats(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["admin", "stats"])
    expect(cached).toEqual(mockAdminStats)
  })

  it("handles error gracefully", async () => {
    vi.mocked(adminApi.getStats).mockRejectedValue({ detail: "Forbidden", status: 403 })

    const { result } = renderHook(() => useAdminStats(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.data).toBeUndefined()
  })

  it("starts in loading state", () => {
    vi.mocked(adminApi.getStats).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useAdminStats(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
})
