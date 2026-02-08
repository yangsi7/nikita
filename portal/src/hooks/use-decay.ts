"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useDecay() {
  return useQuery({
    queryKey: ["portal", "decay"],
    queryFn: portalApi.getDecayStatus,
    staleTime: 15_000, // Refresh frequently
    refetchInterval: 60_000, // Auto-refetch every minute
  })
}
