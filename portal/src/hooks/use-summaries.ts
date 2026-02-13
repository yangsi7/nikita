"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { ApiError } from "@/lib/api/types"

export function useSummaries(limit = 14) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getDailySummaries>>, ApiError>({
    queryKey: ["portal", "summaries", limit],
    queryFn: () => portalApi.getDailySummaries(limit),
    staleTime: STALE_TIMES.history,
    retry: 2,
  })
}
