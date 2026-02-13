"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useLifeEvents(date?: string) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getLifeEvents>>, ApiError>({
    queryKey: ["portal", "life-events", date],
    queryFn: () => portalApi.getLifeEvents(date),
    staleTime: 60_000,
    retry: 2,
  })
}
