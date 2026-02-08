"use client"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { UserSettings } from "@/lib/api/types"
import { toast } from "sonner"

export function useSettings() {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ["portal", "settings"],
    queryFn: portalApi.getSettings,
    staleTime: STALE_TIMES.settings,
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<UserSettings>) => portalApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portal", "settings"] })
      toast.success("Settings saved")
    },
    onError: () => toast.error("Failed to save settings"),
  })

  const linkTelegramMutation = useMutation({
    mutationFn: () => portalApi.linkTelegram(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portal", "settings"] })
      toast.success("Telegram link code generated")
    },
    onError: () => toast.error("Failed to generate link code"),
  })

  const deleteAccountMutation = useMutation({
    mutationFn: () => portalApi.deleteAccount(),
    onSuccess: () => {
      toast.success("Account deleted")
      window.location.href = "/login"
    },
    onError: () => toast.error("Failed to delete account"),
  })

  return {
    ...query,
    updateSettings: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    linkTelegram: linkTelegramMutation.mutateAsync,
    isLinkingTelegram: linkTelegramMutation.isPending,
    deleteAccount: deleteAccountMutation.mutate,
    isDeleting: deleteAccountMutation.isPending,
  }
}
