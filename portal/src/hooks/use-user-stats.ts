"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { ApiError } from "@/lib/api/types"

export function useUserStats() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getStats>>, ApiError>({
    queryKey: ["portal", "stats"],
    queryFn: portalApi.getStats,
    staleTime: STALE_TIMES.stats,
    retry: 2,
  })
}
