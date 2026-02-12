"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useEmotionalStateHistory(hours = 24) {
  return useQuery({
    queryKey: ["portal", "emotional-state-history", hours],
    queryFn: () => portalApi.getEmotionalStateHistory(hours),
    staleTime: 15_000,
  })
}
