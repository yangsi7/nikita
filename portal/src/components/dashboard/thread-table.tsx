"use client"

import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Thread } from "@/lib/api/types"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

interface ThreadTableProps {
  threads: Thread[]
  openCount: number
}

const TYPE_COLORS = {
  question: "bg-cyan-500/10 text-cyan-300 border-cyan-500/30",
  promise: "bg-rose-500/10 text-rose-300 border-rose-500/30",
  topic: "bg-purple-500/10 text-purple-300 border-purple-500/30",
  complaint: "bg-red-500/10 text-red-300 border-red-500/30",
  request: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  revelation: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  conflict: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  goal: "bg-blue-500/10 text-blue-300 border-blue-500/30",
}

const STATUS_COLORS = {
  open: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  resolved: "bg-slate-500/10 text-slate-300 border-slate-500/30",
  expired: "bg-amber-500/10 text-amber-300 border-amber-500/30",
}

export function ThreadTable({ threads, openCount }: ThreadTableProps) {
  if (threads.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No conversation threads yet.
      </div>
    )
  }

  // Sort: open first, then by created_at desc
  const sortedThreads = [...threads].sort((a, b) => {
    if (a.status === "open" && b.status !== "open") return -1
    if (a.status !== "open" && b.status === "open") return 1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">
          {openCount} open {openCount === 1 ? "thread" : "threads"}
        </h3>
      </div>
      <div className="rounded-lg border border-white/10 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-white/10 hover:bg-white/5">
              <TableHead className="text-muted-foreground">Type</TableHead>
              <TableHead className="text-muted-foreground">Content</TableHead>
              <TableHead className="text-muted-foreground">Status</TableHead>
              <TableHead className="text-muted-foreground">Created</TableHead>
              <TableHead className="text-muted-foreground">Resolved</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedThreads.map((thread) => (
              <TableRow
                key={thread.id}
                className="border-white/10 hover:bg-white/5"
              >
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      TYPE_COLORS[
                        thread.thread_type as keyof typeof TYPE_COLORS
                      ] || "bg-white/5 text-foreground/70"
                    )}
                  >
                    {thread.thread_type}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-md">
                  <div className="truncate text-sm text-foreground">
                    {thread.content}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      STATUS_COLORS[
                        thread.status as keyof typeof STATUS_COLORS
                      ] || "bg-white/5 text-foreground/70"
                    )}
                  >
                    {thread.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {format(new Date(thread.created_at), "MMM d, yyyy")}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {thread.resolved_at
                    ? format(new Date(thread.resolved_at), "MMM d, yyyy")
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
