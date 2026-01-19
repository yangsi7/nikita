import { useQuery } from '@tanstack/react-query'
import { adminApiClient } from '@/lib/api/admin-client'
import type { UserListFilters } from '@/lib/api/admin-types'

// Admin poll intervals (as per spec)
const JOBS_POLL_INTERVAL = 30 * 1000 // 30 seconds for jobs
const USERS_POLL_INTERVAL = 60 * 1000 // 60 seconds for users
const SYSTEM_POLL_INTERVAL = 60 * 1000 // 60 seconds for system overview
const VOICE_POLL_INTERVAL = 30 * 1000 // 30 seconds for voice calls
const TEXT_POLL_INTERVAL = 30 * 1000 // 30 seconds for text conversations

/**
 * Hook to check if current user is admin
 */
export function useIsAdmin() {
  return useQuery({
    queryKey: ['isAdmin'],
    queryFn: () => adminApiClient.isAdmin(),
    staleTime: 5 * 60 * 1000, // 5 minutes - admin status rarely changes
  })
}

/**
 * Hook for system overview stats
 * Polls every 60 seconds
 */
export function useSystemOverview() {
  return useQuery({
    queryKey: ['adminSystemOverview'],
    queryFn: () => adminApiClient.getSystemOverview(),
    refetchInterval: SYSTEM_POLL_INTERVAL,
    staleTime: 55 * 1000,
  })
}

/**
 * Hook for scheduled job status
 * Polls every 30 seconds for real-time job monitoring
 */
export function useJobStatus() {
  return useQuery({
    queryKey: ['adminJobStatus'],
    queryFn: () => adminApiClient.getJobStatus(),
    refetchInterval: JOBS_POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

/**
 * Hook for paginated user list
 * Polls every 60 seconds
 */
export function useAdminUsers(filters: UserListFilters = {}) {
  return useQuery({
    queryKey: ['adminUsers', filters],
    queryFn: () => adminApiClient.getUsers(filters),
    refetchInterval: USERS_POLL_INTERVAL,
    staleTime: 55 * 1000,
  })
}

/**
 * Hook for user detail
 * Does not poll - manual refresh
 */
export function useAdminUserDetail(userId: string | null) {
  return useQuery({
    queryKey: ['adminUserDetail', userId],
    queryFn: () => adminApiClient.getUserDetail(userId!),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for user state machines
 * Does not poll - manual refresh
 */
export function useStateMachines(userId: string | null) {
  return useQuery({
    queryKey: ['adminStateMachines', userId],
    queryFn: () => adminApiClient.getStateMachines(userId!),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Voice Monitoring Hooks (Phase 3)
// ============================================================================

/**
 * Hook for voice conversations list
 * Polls every 30 seconds
 */
export function useVoiceConversations(limit = 50, offset = 0, userId?: string) {
  return useQuery({
    queryKey: ['adminVoiceConversations', limit, offset, userId],
    queryFn: () => adminApiClient.getVoiceConversations(limit, offset, userId),
    refetchInterval: VOICE_POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

/**
 * Hook for voice conversation detail
 * Does not poll - manual refresh
 */
export function useVoiceConversationDetail(conversationId: string | null) {
  return useQuery({
    queryKey: ['adminVoiceConversationDetail', conversationId],
    queryFn: () => adminApiClient.getVoiceConversationDetail(conversationId!),
    enabled: !!conversationId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for voice call statistics
 * Polls every 30 seconds
 */
export function useVoiceStats() {
  return useQuery({
    queryKey: ['adminVoiceStats'],
    queryFn: () => adminApiClient.getVoiceStats(),
    refetchInterval: VOICE_POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

/**
 * Hook for ElevenLabs calls list
 * Polls every 30 seconds
 */
export function useElevenLabsCalls(limit = 30) {
  return useQuery({
    queryKey: ['adminElevenLabsCalls', limit],
    queryFn: () => adminApiClient.getElevenLabsCalls(limit),
    refetchInterval: VOICE_POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

/**
 * Hook for ElevenLabs call detail
 * Does not poll - manual refresh
 */
export function useElevenLabsCallDetail(conversationId: string | null) {
  return useQuery({
    queryKey: ['adminElevenLabsCallDetail', conversationId],
    queryFn: () => adminApiClient.getElevenLabsCallDetail(conversationId!),
    enabled: !!conversationId,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Text Monitoring Hooks (Phase 4)
// ============================================================================

/**
 * Hook for text conversations list
 * Polls every 30 seconds
 */
export function useTextConversations(limit = 50, offset = 0, userId?: string) {
  return useQuery({
    queryKey: ['adminTextConversations', limit, offset, userId],
    queryFn: () => adminApiClient.getTextConversations(limit, offset, userId),
    refetchInterval: TEXT_POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

/**
 * Hook for text conversation detail
 * Does not poll - manual refresh
 */
export function useTextConversationDetail(conversationId: string | null) {
  return useQuery({
    queryKey: ['adminTextConversationDetail', conversationId],
    queryFn: () => adminApiClient.getTextConversationDetail(conversationId!),
    enabled: !!conversationId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for text conversation statistics
 * Polls every 30 seconds
 */
export function useTextStats() {
  return useQuery({
    queryKey: ['adminTextStats'],
    queryFn: () => adminApiClient.getTextStats(),
    refetchInterval: TEXT_POLL_INTERVAL,
    staleTime: 25 * 1000,
  })
}

/**
 * Hook for post-processing pipeline status
 * Does not poll - manual refresh
 */
export function usePipelineStatus(conversationId: string | null) {
  return useQuery({
    queryKey: ['adminPipelineStatus', conversationId],
    queryFn: () => adminApiClient.getPipelineStatus(conversationId!),
    enabled: !!conversationId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for user threads
 * Does not poll - manual refresh
 */
export function useThreads(userId: string | null, limit = 50) {
  return useQuery({
    queryKey: ['adminThreads', userId, limit],
    queryFn: () => adminApiClient.getThreads(userId!, limit),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for Nikita thoughts
 * Does not poll - manual refresh
 */
export function useThoughts(userId: string | null, limit = 50) {
  return useQuery({
    queryKey: ['adminThoughts', userId, limit],
    queryFn: () => adminApiClient.getThoughts(userId!, limit),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Prompt Viewing Hooks (Spec 018)
// ============================================================================

/**
 * Hook for user prompts list
 * Does not poll - manual refresh
 */
export function useUserPrompts(userId: string | null, limit = 20) {
  return useQuery({
    queryKey: ['adminUserPrompts', userId, limit],
    queryFn: () => adminApiClient.getUserPrompts(userId!, limit),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for prompt detail
 * Does not poll - manual refresh
 */
export function usePromptDetail(promptId: string | null) {
  return useQuery({
    queryKey: ['adminPromptDetail', promptId],
    queryFn: () => adminApiClient.getPromptDetail(promptId!),
    enabled: !!promptId,
    staleTime: 60 * 1000, // Prompts don't change
  })
}

/**
 * Hook for latest prompt for a user
 * Does not poll - manual refresh
 */
export function useLatestPrompt(userId: string | null) {
  return useQuery({
    queryKey: ['adminLatestPrompt', userId],
    queryFn: () => adminApiClient.getLatestPrompt(userId!),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}
