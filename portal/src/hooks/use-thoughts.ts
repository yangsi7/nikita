"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useThoughts(params?: { limit?: number; offset?: number; type?: string }) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getThoughts>>, ApiError>({
    queryKey: ["portal", "thoughts", params],
    queryFn: () => portalApi.getThoughts(params),
    staleTime: 30_000,
    retry: 2,
  })
}
