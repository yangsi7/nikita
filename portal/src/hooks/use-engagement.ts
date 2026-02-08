"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"

export function useEngagement() {
  return useQuery({
    queryKey: ["portal", "engagement"],
    queryFn: portalApi.getEngagement,
    staleTime: STALE_TIMES.stats,
  })
}
