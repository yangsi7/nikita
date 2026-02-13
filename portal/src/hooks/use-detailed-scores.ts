"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useDetailedScores(days = 30) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getDetailedScoreHistory>>, ApiError>({
    queryKey: ["portal", "detailed-scores", days],
    queryFn: () => portalApi.getDetailedScoreHistory(days),
    staleTime: 60_000,
    retry: 2,
  })
}
