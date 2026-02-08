"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { TranscriptViewer } from "@/components/admin/transcript-viewer"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { formatDateTime, formatDuration } from "@/lib/utils"
import { STALE_TIMES } from "@/lib/constants"
import type { VoiceConversation, ConversationMessage } from "@/lib/api/types"

export default function VoiceMonitorPage() {
  const [selectedConv, setSelectedConv] = useState<string | null>(null)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "voice", "conversations"],
    queryFn: () => adminApi.getVoiceConversations(),
    staleTime: STALE_TIMES.admin,
  })

  if (isLoading) return <LoadingSkeleton variant="table" count={6} />
  if (error) return <ErrorDisplay message="Failed to load voice conversations" onRetry={() => refetch()} />
  if (!data?.items?.length) return <EmptyState message="No voice conversations yet" />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Voice Monitor</h1>
      <div className="glass-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-white/5">
              <TableHead>Date</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((conv: VoiceConversation) => (
              <TableRow key={conv.id} className="border-white/5 cursor-pointer hover:bg-white/5" onClick={() => setSelectedConv(conv.id)}>
                <TableCell className="text-sm">{formatDateTime(conv.started_at)}</TableCell>
                <TableCell className="text-sm">{formatDuration(conv.duration_seconds * 1000)}</TableCell>
                <TableCell className="text-xs font-mono">{conv.user_id.slice(0, 8)}</TableCell>
                <TableCell className="text-xs font-mono">{conv.agent_id.slice(0, 8)}</TableCell>
                <TableCell className="text-xs">{conv.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Sheet open={!!selectedConv} onOpenChange={() => setSelectedConv(null)}>
        <SheetContent className="w-[500px] sm:w-[600px] bg-background border-white/10">
          <SheetHeader>
            <SheetTitle className="text-cyan-400">Voice Transcript</SheetTitle>
          </SheetHeader>
          {selectedConv && <VoiceTranscript convId={selectedConv} />}
        </SheetContent>
      </Sheet>
    </div>
  )
}

function VoiceTranscript({ convId }: { convId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "voice", "conversation", convId],
    queryFn: () => adminApi.getVoiceConversation(convId),
    enabled: !!convId,
  })

  if (isLoading) return <LoadingSkeleton variant="table" count={4} />
  // Voice transcripts stored differently — show raw data
  return (
    <div className="p-4 text-sm text-muted-foreground">
      <pre className="whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre>
    </div>
  )
}
