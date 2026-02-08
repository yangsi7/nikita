"use client"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { STALE_TIMES } from "@/lib/constants"

export function useAdminStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: adminApi.getStats,
    staleTime: STALE_TIMES.admin,
    refetchInterval: 30_000,
  })
}
