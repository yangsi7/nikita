"use client"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { STALE_TIMES } from "@/lib/constants"

interface AdminUsersParams {
  search?: string
  chapter?: number
  engagement?: string
  page?: number
  page_size?: number
}

export function useAdminUsers(params?: AdminUsersParams) {
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: () => adminApi.getUsers(params),
    staleTime: STALE_TIMES.admin,
  })
}
