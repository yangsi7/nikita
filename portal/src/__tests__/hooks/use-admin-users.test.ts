/**
 * Tests for useAdminUsers hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient, createMockAdminUser } from "../utils/test-utils"
import type { AdminUser } from "@/lib/api/types"

vi.mock("@/lib/api/admin", () => ({
  adminApi: {
    getUsers: vi.fn(),
  },
}))

import { adminApi } from "@/lib/api/admin"
import { useAdminUsers } from "@/hooks/use-admin-users"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

describe("useAdminUsers", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches users with no params", async () => {
    const users: AdminUser[] = [createMockAdminUser()]
    vi.mocked(adminApi.getUsers).mockResolvedValue(users)

    const { result } = renderHook(() => useAdminUsers(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(adminApi.getUsers).toHaveBeenCalledWith(undefined)
    expect(result.current.data).toHaveLength(1)
  })

  it("passes search params to the API", async () => {
    vi.mocked(adminApi.getUsers).mockResolvedValue([])

    const params = { search: "alice", chapter: 2 }
    const { result } = renderHook(() => useAdminUsers(params), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(adminApi.getUsers).toHaveBeenCalledWith(params)
  })

  it("includes params in query key for cache isolation", async () => {
    vi.mocked(adminApi.getUsers).mockResolvedValue([])

    const params = { chapter: 3 }
    const qc = createTestQueryClient()
    const { result } = renderHook(() => useAdminUsers(params), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["admin", "users", params])
    expect(cached).toEqual([])
  })

  it("returns empty array when no users", async () => {
    vi.mocked(adminApi.getUsers).mockResolvedValue([])

    const { result } = renderHook(() => useAdminUsers(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(0)
  })

  it("handles API error", async () => {
    vi.mocked(adminApi.getUsers).mockRejectedValue({ detail: "Unauthorized", status: 401 })

    const { result } = renderHook(() => useAdminUsers(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
