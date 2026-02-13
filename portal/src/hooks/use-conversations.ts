"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { ApiError } from "@/lib/api/types"

export function useConversations(page = 1, pageSize = 10) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getConversations>>, ApiError>({
    queryKey: ["portal", "conversations", page, pageSize],
    queryFn: () => portalApi.getConversations(page, pageSize),
    staleTime: STALE_TIMES.history,
    retry: 2,
  })
}

export function useConversation(id: string) {
  return useQuery<Awaited<ReturnType<typeof portalApi.getConversation>>, ApiError>({
    queryKey: ["portal", "conversation", id],
    queryFn: () => portalApi.getConversation(id),
    staleTime: STALE_TIMES.history,
    enabled: !!id,
    retry: 2,
  })
}
