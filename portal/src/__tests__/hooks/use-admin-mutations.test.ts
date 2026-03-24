/**
 * Tests for useAdminMutations hook
 * Verifies mutation calls, cache invalidation, and error handling (toast)
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"

vi.mock("@/lib/api/admin", () => ({
  adminApi: {
    setScore: vi.fn(),
    setChapter: vi.fn(),
    setStatus: vi.fn(),
    setEngagement: vi.fn(),
    resetBoss: vi.fn(),
    clearEngagement: vi.fn(),
    setMetrics: vi.fn(),
    triggerPipeline: vi.fn(),
  },
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

import { adminApi } from "@/lib/api/admin"
import { toast } from "sonner"
import { useAdminMutations } from "@/hooks/use-admin-mutations"

const USER_ID = "user-abc-123"

function createWrapper() {
  const qc = createTestQueryClient()
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
  return { wrapper, qc }
}

describe("useAdminMutations", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("setScore calls adminApi.setScore with correct args", async () => {
    vi.mocked(adminApi.setScore).mockResolvedValue(undefined)
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useAdminMutations(USER_ID), { wrapper })

    act(() => {
      result.current.setScore.mutate({ score: 75, reason: "test bump" })
    })

    await waitFor(() => expect(result.current.setScore.isSuccess).toBe(true))
    expect(adminApi.setScore).toHaveBeenCalledWith(USER_ID, 75, "test bump")
  })

  it("setChapter calls adminApi.setChapter and shows success toast", async () => {
    vi.mocked(adminApi.setChapter).mockResolvedValue(undefined)
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useAdminMutations(USER_ID), { wrapper })

    act(() => {
      result.current.setChapter.mutate({ chapter: 3, reason: "promote" })
    })

    await waitFor(() => expect(result.current.setChapter.isSuccess).toBe(true))
    expect(adminApi.setChapter).toHaveBeenCalledWith(USER_ID, 3, "promote")
    expect(toast.success).toHaveBeenCalledWith("Chapter updated")
  })

  it("invalidates user and users cache on mutation success", async () => {
    vi.mocked(adminApi.setStatus).mockResolvedValue(undefined)
    const { wrapper, qc } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries")

    const { result } = renderHook(() => useAdminMutations(USER_ID), { wrapper })

    act(() => {
      result.current.setStatus.mutate({ status: "game_over", reason: "test" })
    })

    await waitFor(() => expect(result.current.setStatus.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["admin", "user", USER_ID] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["admin", "users"] })
  })

  it("shows error toast on mutation failure", async () => {
    vi.mocked(adminApi.setScore).mockRejectedValue(new Error("Server error"))
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useAdminMutations(USER_ID), { wrapper })

    act(() => {
      result.current.setScore.mutate({ score: 50, reason: "fail test" })
    })

    await waitFor(() => expect(result.current.setScore.isError).toBe(true))
    expect(toast.error).toHaveBeenCalledWith("Failed to update score")
  })

  it("triggerPipeline calls the correct API and shows info toast", async () => {
    vi.mocked(adminApi.triggerPipeline).mockResolvedValue({ job_id: "j1", status: "ok", message: "done" })
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useAdminMutations(USER_ID), { wrapper })

    act(() => {
      result.current.triggerPipeline.mutate(undefined)
    })

    await waitFor(() => expect(result.current.triggerPipeline.isSuccess).toBe(true))
    expect(adminApi.triggerPipeline).toHaveBeenCalledWith(USER_ID)
    expect(toast.info).toHaveBeenCalledWith("Pipeline triggered")
  })

  it("resetBoss calls adminApi.resetBoss", async () => {
    vi.mocked(adminApi.resetBoss).mockResolvedValue(undefined)
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useAdminMutations(USER_ID), { wrapper })

    act(() => {
      result.current.resetBoss.mutate(undefined)
    })

    await waitFor(() => expect(result.current.resetBoss.isSuccess).toBe(true))
    expect(adminApi.resetBoss).toHaveBeenCalledWith(USER_ID)
    expect(toast.success).toHaveBeenCalledWith("Boss reset")
  })
})
