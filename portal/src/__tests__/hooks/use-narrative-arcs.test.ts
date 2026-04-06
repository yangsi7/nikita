/**
 * Tests for useNarrativeArcs hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { NarrativeArcsResponse } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getNarrativeArcs: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useNarrativeArcs } from "@/hooks/use-narrative-arcs"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockArcs: NarrativeArcsResponse = {
  active_arcs: [
    {
      id: "arc-1",
      template_name: "jealousy_test",
      category: "conflict",
      current_stage: "rising",
      stage_progress: 0.4,
      conversations_in_arc: 3,
      max_conversations: 8,
      current_description: "She noticed you liking another girl's photos",
      involved_characters: ["Sarah"],
      emotional_impact: { valence: -0.3, arousal: 0.5 },
      is_active: true,
      started_at: "2026-03-15T10:00:00Z",
      resolved_at: null,
    },
  ],
  resolved_arcs: [
    {
      id: "arc-0",
      template_name: "first_fight",
      category: "conflict",
      current_stage: "resolved",
      stage_progress: 1.0,
      conversations_in_arc: 5,
      max_conversations: 5,
      current_description: "Made up after the fight",
      involved_characters: [],
      emotional_impact: { valence: 0.2, arousal: -0.1 },
      is_active: false,
      started_at: "2026-03-01T10:00:00Z",
      resolved_at: "2026-03-10T10:00:00Z",
    },
  ],
  total_count: 2,
}

describe("useNarrativeArcs", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getNarrativeArcs).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useNarrativeArcs(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches arcs with activeOnly=true by default", async () => {
    vi.mocked(portalApi.getNarrativeArcs).mockResolvedValue(mockArcs)

    const { result } = renderHook(() => useNarrativeArcs(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getNarrativeArcs).toHaveBeenCalledWith(true)
    expect(result.current.data?.active_arcs).toHaveLength(1)
    expect(result.current.data?.resolved_arcs).toHaveLength(1)
  })

  it("passes activeOnly=false to fetch all arcs", async () => {
    vi.mocked(portalApi.getNarrativeArcs).mockResolvedValue(mockArcs)

    const { result } = renderHook(() => useNarrativeArcs(false), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getNarrativeArcs).toHaveBeenCalledWith(false)
  })

  it("includes activeOnly in query key for cache isolation", async () => {
    vi.mocked(portalApi.getNarrativeArcs).mockResolvedValue(mockArcs)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useNarrativeArcs(false), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "narrative-arcs", false])
    expect(cached).toEqual(mockArcs)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getNarrativeArcs).mockRejectedValue({ detail: "Server error", status: 500 })

    const { result } = renderHook(() => useNarrativeArcs(), { wrapper })

    await waitFor(() => expect(portalApi.getNarrativeArcs).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
