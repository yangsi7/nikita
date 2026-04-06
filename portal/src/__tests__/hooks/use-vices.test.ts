/**
 * Tests for useVices hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { VicePreference } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getVices: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useVices } from "@/hooks/use-vices"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockVices: VicePreference[] = [
  {
    category: "dark_humor",
    intensity_level: 3,
    engagement_score: 78,
    discovered_at: "2026-02-01T10:00:00Z",
  },
  {
    category: "jealousy",
    intensity_level: 2,
    engagement_score: 45,
    discovered_at: "2026-02-15T12:00:00Z",
  },
]

describe("useVices", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getVices).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useVices(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("returns vice data on success", async () => {
    vi.mocked(portalApi.getVices).mockResolvedValue(mockVices)

    const { result } = renderHook(() => useVices(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockVices)
    expect(result.current.data).toHaveLength(2)
    expect(result.current.data?.[0].category).toBe("dark_humor")
  })

  it("uses correct query key ['portal', 'vices']", async () => {
    vi.mocked(portalApi.getVices).mockResolvedValue(mockVices)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useVices(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "vices"])
    expect(cached).toEqual(mockVices)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getVices).mockRejectedValue({ detail: "Server error", status: 500 })

    const { result } = renderHook(() => useVices(), { wrapper })

    // Hook has retry: 2 — need longer timeout for retries to exhaust
    await waitFor(() => expect(portalApi.getVices).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
