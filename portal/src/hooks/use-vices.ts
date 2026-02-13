"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { ApiError } from "@/lib/api/types"

export function useVices() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getVices>>, ApiError>({
    queryKey: ["portal", "vices"],
    queryFn: portalApi.getVices,
    staleTime: STALE_TIMES.history,
    retry: 2,
  })
}
