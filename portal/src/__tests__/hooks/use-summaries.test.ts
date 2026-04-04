/**
 * Tests for useSummaries hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { DailySummary } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getDailySummaries: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useSummaries } from "@/hooks/use-summaries"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockSummaries: DailySummary[] = [
  {
    id: "sum-1",
    date: "2026-03-20",
    score_start: 60,
    score_end: 62,
    decay_applied: -0.5,
    conversations_count: 3,
    summary_text: "A warm day of conversation",
    emotional_tone: "affectionate",
  },
  {
    id: "sum-2",
    date: "2026-03-19",
    score_start: 58,
    score_end: 60,
    decay_applied: null,
    conversations_count: 1,
    summary_text: null,
    emotional_tone: null,
  },
]

describe("useSummaries", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getDailySummaries).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useSummaries(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches summaries with default limit of 14", async () => {
    vi.mocked(portalApi.getDailySummaries).mockResolvedValue(mockSummaries)

    const { result } = renderHook(() => useSummaries(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getDailySummaries).toHaveBeenCalledWith(14)
    expect(result.current.data).toHaveLength(2)
  })

  it("passes custom limit parameter", async () => {
    vi.mocked(portalApi.getDailySummaries).mockResolvedValue(mockSummaries)

    const { result } = renderHook(() => useSummaries(7), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getDailySummaries).toHaveBeenCalledWith(7)
  })

  it("includes limit in query key for cache isolation", async () => {
    vi.mocked(portalApi.getDailySummaries).mockResolvedValue(mockSummaries)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useSummaries(7), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "summaries", 7])
    expect(cached).toEqual(mockSummaries)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getDailySummaries).mockRejectedValue({ detail: "Not found", status: 404 })

    const { result } = renderHook(() => useSummaries(), { wrapper })

    await waitFor(() => expect(portalApi.getDailySummaries).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
