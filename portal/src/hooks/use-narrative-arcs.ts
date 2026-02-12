"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useNarrativeArcs(activeOnly = true) {
  return useQuery({
    queryKey: ["portal", "narrative-arcs", activeOnly],
    queryFn: () => portalApi.getNarrativeArcs(activeOnly),
    staleTime: 60_000,
  })
}
