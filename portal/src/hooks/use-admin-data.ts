import { useQuery } from '@tanstack/react-query'
import { adminApiClient } from '@/lib/api/admin-client'
import type { UserListFilters } from '@/lib/api/admin-types'

// Admin poll intervals (as per spec)
const JOBS_POLL_INTERVAL = 30 * 1000 // 30 seconds for jobs
const USERS_POLL_INTERVAL = 60 * 1000 // 60 seconds for users
const SYSTEM_POLL_INTERVAL = 60 * 1000 // 60 seconds for system overview

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
