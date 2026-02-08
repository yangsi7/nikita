"use client"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { STALE_TIMES } from "@/lib/constants"

export function useAdminUser(id: string) {
  return useQuery({
    queryKey: ["admin", "user", id],
    queryFn: () => adminApi.getUser(id),
    staleTime: STALE_TIMES.admin,
    enabled: !!id,
  })
}

export function useAdminUserPipelineHistory(id: string) {
  return useQuery({
    queryKey: ["admin", "user", id, "pipeline-history"],
    queryFn: () => adminApi.getPipelineHistory(id),
    staleTime: STALE_TIMES.admin,
    enabled: !!id,
  })
}
