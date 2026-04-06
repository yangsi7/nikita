/**
 * Tests for usePsycheTips hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { PsycheTipsData } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getPsycheTips: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { usePsycheTips } from "@/hooks/use-psyche-tips"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockPsycheTips: PsycheTipsData = {
  attachment_style: "anxious",
  defense_mode: "guarded",
  emotional_tone: "melancholic",
  vulnerability_level: 0.3,
  behavioral_tips: [
    "Ask about her day before talking about yours",
    "Avoid bringing up the fight from last week",
  ],
  topics_to_encourage: ["her childhood memories", "travel dreams"],
  topics_to_avoid: ["your female coworker", "being busy"],
  internal_monologue: "I wonder if he really cares about me...",
  generated_at: "2026-03-20T10:00:00Z",
}

describe("usePsycheTips", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getPsycheTips).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => usePsycheTips(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("returns psyche tips data on success", async () => {
    vi.mocked(portalApi.getPsycheTips).mockResolvedValue(mockPsycheTips)

    const { result } = renderHook(() => usePsycheTips(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.attachment_style).toBe("anxious")
    expect(result.current.data?.behavioral_tips).toHaveLength(2)
    expect(result.current.data?.topics_to_avoid).toContain("being busy")
  })

  it("uses correct query key ['portal', 'psyche-tips']", async () => {
    vi.mocked(portalApi.getPsycheTips).mockResolvedValue(mockPsycheTips)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => usePsycheTips(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "psyche-tips"])
    expect(cached).toEqual(mockPsycheTips)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getPsycheTips).mockRejectedValue({ detail: "Not found", status: 404 })

    const { result } = renderHook(() => usePsycheTips(), { wrapper })

    await waitFor(() => expect(portalApi.getPsycheTips).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
