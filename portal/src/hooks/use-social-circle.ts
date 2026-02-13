"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useSocialCircle() {
  return useQuery<Awaited<ReturnType<typeof portalApi.getSocialCircle>>, ApiError>({
    queryKey: ["portal", "social-circle"],
    queryFn: portalApi.getSocialCircle,
    staleTime: 300_000,
    retry: 2,
  })
}
