"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useEmotionalStateHistory(hours = 24) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getEmotionalStateHistory>>, ApiError>({
    queryKey: ["portal", "emotional-state-history", hours],
    queryFn: () => portalApi.getEmotionalStateHistory(hours),
    staleTime: 15_000,
    retry: 2,
  })
}
