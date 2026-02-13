"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { ApiError } from "@/lib/api/types"

export function useEngagement() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getEngagement>>, ApiError>({
    queryKey: ["portal", "engagement"],
    queryFn: portalApi.getEngagement,
    staleTime: STALE_TIMES.stats,
    retry: 2,
  })
}
