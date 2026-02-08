"use client"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { STALE_TIMES } from "@/lib/constants"

export function useAdminPipeline() {
  return useQuery({
    queryKey: ["admin", "pipeline-health"],
    queryFn: adminApi.getPipelineHealth,
    staleTime: STALE_TIMES.admin,
    refetchInterval: 30_000,
  })
}
