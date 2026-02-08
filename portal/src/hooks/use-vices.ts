"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"

export function useVices() {
  return useQuery({
    queryKey: ["portal", "vices"],
    queryFn: portalApi.getVices,
    staleTime: STALE_TIMES.history,
  })
}
