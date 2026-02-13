"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useEmotionalState() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getEmotionalState>>, ApiError>({
    queryKey: ["portal", "emotional-state"],
    queryFn: portalApi.getEmotionalState,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 2,
  })
}
