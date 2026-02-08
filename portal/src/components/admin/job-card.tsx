"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { formatDateTime } from "@/lib/utils"
import { adminApi } from "@/lib/api/admin"
import { toast } from "sonner"
import { useState } from "react"
import { Play, CheckCircle, XCircle, Loader2 } from "lucide-react"
import type { JobStatus } from "@/lib/api/types"

interface JobCardProps {
  job: JobStatus
}

const statusIcons = {
  success: <CheckCircle className="h-4 w-4 text-emerald-400" />,
  failed: <XCircle className="h-4 w-4 text-red-400" />,
  running: <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />,
  unknown: <div className="h-4 w-4 rounded-full bg-zinc-500" />,
}

export function JobCard({ job }: JobCardProps) {
  const [triggering, setTriggering] = useState(false)

  async function handleTrigger() {
    setTriggering(true)
    try {
      await adminApi.triggerJob(job.name)
      toast.success(`Job "${job.name}" triggered`)
    } catch {
      toast.error(`Failed to trigger "${job.name}"`)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <GlassCard className="p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {statusIcons[job.status]}
          <div>
            <p className="text-sm font-medium capitalize">{job.name.replace(/-/g, " ")}</p>
            <p className="text-xs text-muted-foreground">
              Last: {job.last_run ? formatDateTime(job.last_run) : "Never"}
            </p>
          </div>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Play className="h-3 w-3" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Trigger {job.name}?</DialogTitle>
              <DialogDescription>This will manually run the background job.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline">Cancel</Button>
              <Button onClick={handleTrigger} disabled={triggering}>
                {triggering ? "Triggering..." : "Run Now"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      <div className="flex gap-3 mt-3 text-xs text-muted-foreground">
        <span>{job.executions_24h} runs (24h)</span>
        {job.failures_24h > 0 && <span className="text-red-400">{job.failures_24h} failures</span>}
      </div>
    </GlassCard>
  )
}
