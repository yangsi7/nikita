"use client"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"

export function useConversations(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["portal", "conversations", page, pageSize],
    queryFn: () => portalApi.getConversations(page, pageSize),
    staleTime: STALE_TIMES.history,
  })
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ["portal", "conversation", id],
    queryFn: () => portalApi.getConversation(id),
    staleTime: STALE_TIMES.history,
    enabled: !!id,
  })
}
