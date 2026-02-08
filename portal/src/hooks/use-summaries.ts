"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"

export function useSummaries(limit = 14) {
  return useQuery({
    queryKey: ["portal", "summaries", limit],
    queryFn: () => portalApi.getDailySummaries(limit),
    staleTime: STALE_TIMES.history,
  })
}
