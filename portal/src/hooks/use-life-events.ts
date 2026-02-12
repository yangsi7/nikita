"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useLifeEvents(date?: string) {
  return useQuery({
    queryKey: ["portal", "life-events", date],
    queryFn: () => portalApi.getLifeEvents(date),
    staleTime: 60_000,
  })
}
