/**
 * Tests for useLifeEvents hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { LifeEventsResponse } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getLifeEvents: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useLifeEvents } from "@/hooks/use-life-events"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockLifeEvents: LifeEventsResponse = {
  events: [
    {
      event_id: "le-1",
      time_of_day: "morning",
      domain: "work",
      event_type: "meeting",
      description: "Had a frustrating meeting with her boss",
      entities: ["boss", "project"],
      importance: 7,
      emotional_impact: {
        arousal_delta: 0.2,
        valence_delta: -0.3,
        dominance_delta: -0.1,
        intimacy_delta: 0,
      },
      narrative_arc_id: null,
    },
    {
      event_id: "le-2",
      time_of_day: "evening",
      domain: "social",
      event_type: "outing",
      description: "Went to dinner with friends",
      entities: ["Sarah", "restaurant"],
      importance: 5,
      emotional_impact: null,
      narrative_arc_id: "arc-1",
    },
  ],
  date: "2026-03-20",
  total_count: 2,
}

describe("useLifeEvents", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getLifeEvents).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useLifeEvents(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches life events with no date by default", async () => {
    vi.mocked(portalApi.getLifeEvents).mockResolvedValue(mockLifeEvents)

    const { result } = renderHook(() => useLifeEvents(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getLifeEvents).toHaveBeenCalledWith(undefined)
    expect(result.current.data?.events).toHaveLength(2)
    expect(result.current.data?.date).toBe("2026-03-20")
  })

  it("passes date parameter to API call", async () => {
    vi.mocked(portalApi.getLifeEvents).mockResolvedValue(mockLifeEvents)

    const { result } = renderHook(() => useLifeEvents("2026-03-20"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getLifeEvents).toHaveBeenCalledWith("2026-03-20")
  })

  it("includes date in query key for cache isolation", async () => {
    vi.mocked(portalApi.getLifeEvents).mockResolvedValue(mockLifeEvents)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useLifeEvents("2026-03-20"), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "life-events", "2026-03-20"])
    expect(cached).toEqual(mockLifeEvents)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getLifeEvents).mockRejectedValue({ detail: "Not found", status: 404 })

    const { result } = renderHook(() => useLifeEvents(), { wrapper })

    await waitFor(() => expect(portalApi.getLifeEvents).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
