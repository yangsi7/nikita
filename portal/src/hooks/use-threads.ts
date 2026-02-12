"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useThreads(params?: { status?: string; type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["portal", "threads", params],
    queryFn: () => portalApi.getThreads(params),
    staleTime: 60_000,
  })
}
