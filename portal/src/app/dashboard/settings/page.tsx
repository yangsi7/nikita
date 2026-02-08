"use client"

import { useState } from "react"
import { useSettings } from "@/hooks/use-settings"
import { GlassCard } from "@/components/glass/glass-card"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { Separator } from "@/components/ui/separator"
import { Link2, Unlink, Trash2 } from "lucide-react"

const timezones = [
  "UTC", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
  "Europe/London", "Europe/Berlin", "Europe/Zurich", "Asia/Tokyo", "Asia/Shanghai",
  "Australia/Sydney",
]

export default function SettingsPage() {
  const { data: settings, isLoading, error, refetch, updateSettings, isUpdating, linkTelegram, isLinkingTelegram, deleteAccount, isDeleting } = useSettings()
  const [telegramCode, setTelegramCode] = useState<string | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={3} />
  if (error || !settings) return <ErrorDisplay message="Failed to load settings" onRetry={() => refetch()} />

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-lg font-semibold">Settings</h2>

      {/* Account */}
      <GlassCardWithHeader title="Account">
        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground">Email</label>
            <Input value={settings.email} disabled className="bg-white/5 border-white/10" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Timezone</label>
            <Select
              value={settings.timezone ?? "UTC"}
              onValueChange={(tz) => updateSettings({ timezone: tz })}
              disabled={isUpdating}
            >
              <SelectTrigger className="bg-white/5 border-white/10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {timezones.map((tz) => (
                  <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </GlassCardWithHeader>

      {/* Telegram */}
      <GlassCardWithHeader title="Telegram" description="Connect your Telegram account">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {settings.telegram_linked ? (
              <>
                <Badge variant="outline" className="text-emerald-400 border-emerald-400/30">Connected</Badge>
                {settings.telegram_username && (
                  <span className="text-sm text-muted-foreground">@{settings.telegram_username}</span>
                )}
              </>
            ) : (
              <Badge variant="outline" className="text-muted-foreground">Not connected</Badge>
            )}
          </div>
          {!settings.telegram_linked && (
            <Button
              variant="outline"
              size="sm"
              disabled={isLinkingTelegram}
              onClick={async () => {
                const result = await linkTelegram()
                if (result?.code) setTelegramCode(result.code)
              }}
            >
              <Link2 className="mr-1 h-3 w-3" />
              {isLinkingTelegram ? "Generating..." : "Link Telegram"}
            </Button>
          )}
        </div>
        {telegramCode && (
          <div className="mt-4 rounded-lg bg-white/5 p-3">
            <p className="text-xs text-muted-foreground mb-1">Send this code to @Nikita_my_bot on Telegram:</p>
            <code className="text-lg font-mono text-rose-400">{telegramCode}</code>
          </div>
        )}
      </GlassCardWithHeader>

      {/* Danger Zone */}
      <Separator className="bg-white/5" />
      <GlassCard variant="danger" className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-red-400">Danger Zone</h3>
            <p className="text-xs text-muted-foreground">Permanently delete your account and all data</p>
          </div>
          <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
            <DialogTrigger asChild>
              <Button variant="destructive" size="sm">
                <Trash2 className="mr-1 h-3 w-3" />
                Delete Account
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Are you sure?</DialogTitle>
                <DialogDescription>
                  This will permanently delete your account, all conversations, and game progress. This cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>Cancel</Button>
                <Button variant="destructive" disabled={isDeleting} onClick={() => deleteAccount()}>
                  {isDeleting ? "Deleting..." : "Delete Everything"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </GlassCard>
    </div>
  )
}
