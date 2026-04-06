/**
 * Tests for useUserStats hook
 * Mocks portalApi.getStats and verifies query behaviour
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient, createMockUser } from "../utils/test-utils"


// Mock the portalApi module
vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getStats: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useUserStats } from "@/hooks/use-user-stats"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

describe("useUserStats", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns data on success", async () => {
    const mockStats = createMockUser()
    vi.mocked(portalApi.getStats).mockResolvedValue(mockStats)

    const { result } = renderHook(() => useUserStats(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockStats)
    expect(portalApi.getStats).toHaveBeenCalledOnce()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getStats).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useUserStats(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("sets isError after failed query", async () => {
    vi.mocked(portalApi.getStats).mockRejectedValue({ detail: "Unauthorized", status: 401 })

    const { result } = renderHook(() => useUserStats(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 })
    expect(result.current.data).toBeUndefined()
  })

  it("uses correct query key ['portal', 'stats']", async () => {
    const mockStats = createMockUser()
    vi.mocked(portalApi.getStats).mockResolvedValue(mockStats)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useUserStats(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "stats"])
    expect(cached).toEqual(mockStats)
  })
})
