"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { ApiError } from "@/lib/api/types"

export function useScoreHistory(days = 30) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getScoreHistory>>, ApiError>({
    queryKey: ["portal", "score-history", days],
    queryFn: () => portalApi.getScoreHistory(days),
    staleTime: STALE_TIMES.history,
    retry: 2,
  })
}
