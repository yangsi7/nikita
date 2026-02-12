"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useEmotionalState() {
  return useQuery({
    queryKey: ["portal", "emotional-state"],
    queryFn: portalApi.getEmotionalState,
    staleTime: 15_000,
    refetchInterval: 30_000,
  })
}
