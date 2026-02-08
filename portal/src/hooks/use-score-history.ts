"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"

export function useScoreHistory(days = 30) {
  return useQuery({
    queryKey: ["portal", "score-history", days],
    queryFn: () => portalApi.getScoreHistory(days),
    staleTime: STALE_TIMES.history,
  })
}
