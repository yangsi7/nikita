"use client"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { toast } from "sonner"

// UX-004/FE-009: Admin mutations must not retry — avoid duplicate writes on transient errors.
const ADMIN_MUTATION_DEFAULTS = { retry: 0 } as const

export function useAdminMutations(userId: string) {
  const queryClient = useQueryClient()

  const invalidateUser = () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "user", userId] })
    queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
  }

  const setScore = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: ({ score, reason }: { score: number; reason: string }) =>
      adminApi.setScore(userId, score, reason),
    onSuccess: () => { invalidateUser(); toast.success("Score updated") },
    onError: () => toast.error("Failed to update score"),
  })

  const setChapter = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: ({ chapter, reason }: { chapter: number; reason: string }) =>
      adminApi.setChapter(userId, chapter, reason),
    onSuccess: () => { invalidateUser(); toast.success("Chapter updated") },
    onError: () => toast.error("Failed to update chapter"),
  })

  const setStatus = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: ({ status, reason }: { status: string; reason: string }) =>
      adminApi.setStatus(userId, status, reason),
    onSuccess: () => { invalidateUser(); toast.success("Status updated") },
    onError: () => toast.error("Failed to update status"),
  })

  const setEngagement = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: ({ state, reason }: { state: string; reason: string }) =>
      adminApi.setEngagement(userId, state, reason),
    onSuccess: () => { invalidateUser(); toast.success("Engagement updated") },
    onError: () => toast.error("Failed to update engagement"),
  })

  const resetBoss = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: (_reason?: string) => adminApi.resetBoss(userId),
    onSuccess: () => { invalidateUser(); toast.success("Boss reset") },
    onError: () => toast.error("Failed to reset boss"),
  })

  const clearEngagement = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: (_reason?: string) => adminApi.clearEngagement(userId),
    onSuccess: () => { invalidateUser(); toast.success("Engagement cleared") },
    onError: () => toast.error("Failed to clear engagement"),
  })

  const setMetrics = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: (data: { intimacy?: number; passion?: number; trust?: number; secureness?: number; reason: string }) =>
      adminApi.setMetrics(userId, data),
    onSuccess: () => { invalidateUser(); toast.success("Metrics updated") },
    onError: () => toast.error("Failed to update metrics"),
  })

  const triggerPipeline = useMutation({
    ...ADMIN_MUTATION_DEFAULTS,
    mutationFn: (_reason?: string) => adminApi.triggerPipeline(userId),
    onSuccess: () => { toast.info("Pipeline triggered") },
    onError: () => toast.error("Failed to trigger pipeline"),
  })

  return { setScore, setChapter, setStatus, setEngagement, resetBoss, clearEngagement, setMetrics, triggerPipeline }
}
