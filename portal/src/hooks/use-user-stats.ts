"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"

export function useUserStats() {
  return useQuery({
    queryKey: ["portal", "stats"],
    queryFn: portalApi.getStats,
    staleTime: STALE_TIMES.stats,
  })
}
