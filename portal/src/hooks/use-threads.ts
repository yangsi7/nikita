"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import type { ApiError } from "@/lib/api/types"

export function useThreads(params?: { status?: string; type?: string; limit?: number }) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getThreads>>, ApiError>({
    queryKey: ["portal", "threads", params],
    queryFn: () => portalApi.getThreads(params),
    staleTime: 60_000,
    retry: 2,
  })
}
