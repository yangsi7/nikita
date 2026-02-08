"use client"

import { useState } from "react"
import { GlassCard } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { useAdminMutations } from "@/hooks/use-admin-mutations"
import { CHAPTER_ROMAN, ENGAGEMENT_STATES, GAME_STATUSES } from "@/lib/constants"
import { Shield } from "lucide-react"

interface GodModePanelProps {
  userId: string
}

interface MutationDialogProps {
  title: string
  description: string
  children: React.ReactNode
  onConfirm: () => void
  isPending: boolean
}

function MutationDialog({ title, description, children, onConfirm, isPending }: MutationDialogProps) {
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={() => { onConfirm(); setOpen(false) }} disabled={isPending}>
            {isPending ? "Applying..." : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function GodModePanel({ userId }: GodModePanelProps) {
  const mutations = useAdminMutations(userId)
  const [score, setScore] = useState("")
  const [chapter, setChapter] = useState("")
  const [status, setStatus] = useState("")
  const [engagement, setEngagement] = useState("")
  const [reason, setReason] = useState("")

  return (
    <GlassCard variant="amber" className="p-6">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-4 w-4 text-amber-400" />
        <h3 className="text-sm font-bold text-amber-400">God Mode</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Set Score */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">Set Score (0-100)</label>
          <div className="flex gap-2">
            <Input type="number" min={0} max={100} value={score} onChange={(e) => setScore(e.target.value)} className="bg-white/5 border-white/10" placeholder="0-100" />
            <MutationDialog title="Set Score" description={`Set score to ${score}?`} onConfirm={() => mutations.setScore.mutate({ score: Number(score), reason: reason || "Admin override" })} isPending={mutations.setScore.isPending}>
              <Button variant="outline" size="sm" disabled={!score}>Set</Button>
            </MutationDialog>
          </div>
        </div>

        {/* Set Chapter */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">Set Chapter</label>
          <div className="flex gap-2">
            <Select value={chapter} onValueChange={setChapter}>
              <SelectTrigger className="bg-white/5 border-white/10"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                {[1,2,3,4,5].map(c => <SelectItem key={c} value={String(c)}>Ch {CHAPTER_ROMAN[c]}</SelectItem>)}
              </SelectContent>
            </Select>
            <MutationDialog title="Set Chapter" description={`Set chapter to ${chapter}?`} onConfirm={() => mutations.setChapter.mutate({ chapter: Number(chapter), reason: reason || "Admin override" })} isPending={mutations.setChapter.isPending}>
              <Button variant="outline" size="sm" disabled={!chapter}>Set</Button>
            </MutationDialog>
          </div>
        </div>

        {/* Set Status */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">Set Game Status</label>
          <div className="flex gap-2">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="bg-white/5 border-white/10"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                {GAME_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
            <MutationDialog title="Set Status" description={`Set status to ${status}?`} onConfirm={() => mutations.setStatus.mutate({ status, reason: reason || "Admin override" })} isPending={mutations.setStatus.isPending}>
              <Button variant="outline" size="sm" disabled={!status}>Set</Button>
            </MutationDialog>
          </div>
        </div>

        {/* Set Engagement */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">Set Engagement</label>
          <div className="flex gap-2">
            <Select value={engagement} onValueChange={setEngagement}>
              <SelectTrigger className="bg-white/5 border-white/10"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                {ENGAGEMENT_STATES.map(s => <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>)}
              </SelectContent>
            </Select>
            <MutationDialog title="Set Engagement" description={`Set engagement to ${engagement}?`} onConfirm={() => mutations.setEngagement.mutate({ state: engagement, reason: reason || "Admin override" })} isPending={mutations.setEngagement.isPending}>
              <Button variant="outline" size="sm" disabled={!engagement}>Set</Button>
            </MutationDialog>
          </div>
        </div>
      </div>

      <Separator className="my-4 bg-amber-500/20" />

      {/* Reason + Action Buttons */}
      <div className="space-y-3">
        <div>
          <label className="text-xs text-muted-foreground">Reason (for all actions)</label>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why are you doing this?" className="bg-white/5 border-white/10" />
        </div>
        <div className="flex gap-2">
          <MutationDialog title="Reset Boss" description="Reset boss encounter?" onConfirm={() => mutations.resetBoss.mutate(reason || "Admin override")} isPending={mutations.resetBoss.isPending}>
            <Button variant="outline" size="sm">Reset Boss</Button>
          </MutationDialog>
          <MutationDialog title="Clear Engagement" description="Clear engagement state?" onConfirm={() => mutations.clearEngagement.mutate(reason || "Admin override")} isPending={mutations.clearEngagement.isPending}>
            <Button variant="outline" size="sm">Clear Engagement</Button>
          </MutationDialog>
          <MutationDialog title="Trigger Pipeline" description="Trigger pipeline for this user?" onConfirm={() => mutations.triggerPipeline.mutate(reason || "Admin override")} isPending={mutations.triggerPipeline.isPending}>
            <Button variant="outline" size="sm" className="text-cyan-400 border-cyan-400/30">Trigger Pipeline</Button>
          </MutationDialog>
        </div>
      </div>
    </GlassCard>
  )
}
