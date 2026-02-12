"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"

export function useSocialCircle() {
  return useQuery({
    queryKey: ["portal", "social-circle"],
    queryFn: portalApi.getSocialCircle,
    staleTime: 300_000,
  })
}
