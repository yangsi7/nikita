"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useThoughts(params?: { limit?: number; offset?: number; type?: string }) {
  return useQuery({
    queryKey: ["portal", "thoughts", params],
    queryFn: () => portalApi.getThoughts(params),
    staleTime: 30_000,
  })
}
