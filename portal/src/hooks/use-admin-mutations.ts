"use client"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { toast } from "sonner"

export function useAdminMutations(userId: string) {
  const queryClient = useQueryClient()

  const invalidateUser = () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "user", userId] })
    queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
  }

  const setScore = useMutation({
    mutationFn: ({ score, reason }: { score: number; reason: string }) =>
      adminApi.setScore(userId, score, reason),
    onSuccess: () => { invalidateUser(); toast.success("Score updated") },
    onError: () => toast.error("Failed to update score"),
  })

  const setChapter = useMutation({
    mutationFn: ({ chapter, reason }: { chapter: number; reason: string }) =>
      adminApi.setChapter(userId, chapter, reason),
    onSuccess: () => { invalidateUser(); toast.success("Chapter updated") },
    onError: () => toast.error("Failed to update chapter"),
  })

  const setStatus = useMutation({
    mutationFn: ({ status, reason }: { status: string; reason: string }) =>
      adminApi.setStatus(userId, status, reason),
    onSuccess: () => { invalidateUser(); toast.success("Status updated") },
    onError: () => toast.error("Failed to update status"),
  })

  const setEngagement = useMutation({
    mutationFn: ({ state, reason }: { state: string; reason: string }) =>
      adminApi.setEngagement(userId, state, reason),
    onSuccess: () => { invalidateUser(); toast.success("Engagement updated") },
    onError: () => toast.error("Failed to update engagement"),
  })

  const resetBoss = useMutation({
    mutationFn: (reason: string) => adminApi.resetBoss(userId, reason),
    onSuccess: () => { invalidateUser(); toast.success("Boss reset") },
    onError: () => toast.error("Failed to reset boss"),
  })

  const clearEngagement = useMutation({
    mutationFn: (reason: string) => adminApi.clearEngagement(userId, reason),
    onSuccess: () => { invalidateUser(); toast.success("Engagement cleared") },
    onError: () => toast.error("Failed to clear engagement"),
  })

  const setMetrics = useMutation({
    mutationFn: (data: { intimacy?: number; passion?: number; trust?: number; secureness?: number; reason: string }) =>
      adminApi.setMetrics(userId, data),
    onSuccess: () => { invalidateUser(); toast.success("Metrics updated") },
    onError: () => toast.error("Failed to update metrics"),
  })

  const triggerPipeline = useMutation({
    mutationFn: (reason: string) => adminApi.triggerPipeline(userId, reason),
    onSuccess: () => { toast.info("Pipeline triggered") },
    onError: () => toast.error("Failed to trigger pipeline"),
  })

  return { setScore, setChapter, setStatus, setEngagement, resetBoss, clearEngagement, setMetrics, triggerPipeline }
}
