"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useNarrativeArcs(activeOnly = true) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getNarrativeArcs>>, ApiError>({
    queryKey: ["portal", "narrative-arcs", activeOnly],
    queryFn: () => portalApi.getNarrativeArcs(activeOnly),
    staleTime: 60_000,
    retry: 2,
  })
}
