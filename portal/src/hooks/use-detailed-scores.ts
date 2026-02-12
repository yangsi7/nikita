"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useDetailedScores(days = 30) {
  return useQuery({
    queryKey: ["portal", "detailed-scores", days],
    queryFn: () => portalApi.getDetailedScoreHistory(days),
    staleTime: 60_000,
  })
}
