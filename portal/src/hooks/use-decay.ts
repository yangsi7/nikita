"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useDecay() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getDecayStatus>>, ApiError>({
    queryKey: ["portal", "decay"],
    queryFn: portalApi.getDecayStatus,
    staleTime: 15_000, // Refresh frequently
    refetchInterval: 60_000, // Auto-refetch every minute
    retry: 2,
  })
}
