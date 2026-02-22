"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function usePsycheTips() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getPsycheTips>>, ApiError>({
    queryKey: ["portal", "psyche-tips"],
    queryFn: portalApi.getPsycheTips,
    staleTime: 60_000,
    retry: 2,
  })
}
