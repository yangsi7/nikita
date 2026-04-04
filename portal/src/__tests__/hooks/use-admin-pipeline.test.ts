/**
 * Tests for useAdminPipeline hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { PipelineHealth } from "@/lib/api/types"

vi.mock("@/lib/api/admin", () => ({
  adminApi: {
    getPipelineHealth: vi.fn(),
  },
}))

import { adminApi } from "@/lib/api/admin"
import { useAdminPipeline } from "@/hooks/use-admin-pipeline"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockPipelineHealth: PipelineHealth = {
  status: "healthy",
  pipeline_version: "2.1.0",
  stages: [
    {
      name: "extraction",
      is_critical: true,
      avg_duration_ms: 120,
      success_rate: 0.99,
      runs_24h: 150,
      failures_24h: 1,
      timeout_seconds: 30,
    },
    {
      name: "memory_update",
      is_critical: true,
      avg_duration_ms: 250,
      success_rate: 0.97,
      runs_24h: 148,
      failures_24h: 4,
      timeout_seconds: 60,
    },
  ],
  total_runs_24h: 150,
  overall_success_rate: 0.98,
  avg_pipeline_duration_ms: 1200,
  last_run_at: "2026-03-20T15:00:00Z",
}

describe("useAdminPipeline", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(adminApi.getPipelineHealth).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useAdminPipeline(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("returns pipeline health data on success", async () => {
    vi.mocked(adminApi.getPipelineHealth).mockResolvedValue(mockPipelineHealth)

    const { result } = renderHook(() => useAdminPipeline(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe("healthy")
    expect(result.current.data?.stages).toHaveLength(2)
    expect(result.current.data?.overall_success_rate).toBe(0.98)
  })

  it("uses correct query key ['admin', 'pipeline-health']", async () => {
    vi.mocked(adminApi.getPipelineHealth).mockResolvedValue(mockPipelineHealth)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useAdminPipeline(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["admin", "pipeline-health"])
    expect(cached).toEqual(mockPipelineHealth)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(adminApi.getPipelineHealth).mockRejectedValue({ detail: "Forbidden", status: 403 })

    const { result } = renderHook(() => useAdminPipeline(), { wrapper })

    await waitFor(() => expect(adminApi.getPipelineHealth).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
