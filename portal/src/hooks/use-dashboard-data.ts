import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'

// Poll interval: 30 seconds (as per spec)
const POLL_INTERVAL = 30 * 1000

export function useUserStats() {
  return useQuery({
    queryKey: ['userStats'],
    queryFn: () => apiClient.getUserStats(),
    refetchInterval: POLL_INTERVAL,
    staleTime: 25 * 1000, // 25 seconds
  })
}

export function useEngagement() {
  return useQuery({
    queryKey: ['engagement'],
    queryFn: () => apiClient.getEngagement(),
    refetchInterval: POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

export function useVices() {
  return useQuery({
    queryKey: ['vices'],
    queryFn: () => apiClient.getVices(),
    refetchInterval: POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

export function useConversations(limit = 10) {
  return useQuery({
    queryKey: ['conversations', limit],
    queryFn: () => apiClient.getConversations(limit),
    refetchInterval: POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

export function useDailySummary(date: string) {
  return useQuery({
    queryKey: ['dailySummary', date],
    queryFn: () => apiClient.getDailySummary(date),
    enabled: !!date, // Only fetch if date is provided
    staleTime: 60 * 1000, // Summaries don't change often
  })
}

export function useDecayStatus() {
  return useQuery({
    queryKey: ['decayStatus'],
    queryFn: () => apiClient.getDecayStatus(),
    refetchInterval: POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

export function useScoreHistory(days = 30) {
  return useQuery({
    queryKey: ['scoreHistory', days],
    queryFn: () => apiClient.getScoreHistory(days),
    refetchInterval: POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}
