"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { formatDateTime } from "@/lib/utils"
import { STALE_TIMES } from "@/lib/constants"
import type { PromptDetail } from "@/lib/api/types"

export default function PromptsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "prompts", page],
    queryFn: () => adminApi.getPrompts(page),
    staleTime: STALE_TIMES.admin,
  })

  const { data: detail } = useQuery({
    queryKey: ["admin", "prompt", selectedId],
    queryFn: () => adminApi.getPrompt(selectedId!),
    enabled: !!selectedId,
  })

  if (isLoading) return <LoadingSkeleton variant="table" count={6} />
  if (error) return <ErrorDisplay message="Failed to load prompts" onRetry={() => refetch()} />
  if (!data?.items?.length) return <EmptyState message="No prompts generated yet" />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Prompt Inspector</h1>
      <div className="glass-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-white/5">
              <TableHead>User</TableHead>
              <TableHead>Platform</TableHead>
              <TableHead>Tokens</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((prompt) => (
              <TableRow key={prompt.id} className="border-white/5 cursor-pointer hover:bg-white/5" onClick={() => setSelectedId(prompt.id)}>
                <TableCell className="text-xs font-mono">{prompt.user_id.slice(0, 8)}</TableCell>
                <TableCell className="text-sm">{prompt.platform}</TableCell>
                <TableCell className="text-sm">{prompt.token_count.toLocaleString()}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{formatDateTime(prompt.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Sheet open={!!selectedId} onOpenChange={() => setSelectedId(null)}>
        <SheetContent className="w-[600px] sm:w-[700px] bg-background border-white/10">
          <SheetHeader>
            <SheetTitle className="text-cyan-400">Prompt Detail</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="mt-4 space-y-4">
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>Template: {(detail as PromptDetail).meta_prompt_template}</span>
                <span>{(detail as PromptDetail).token_count.toLocaleString()} tokens</span>
              </div>
              <ScrollArea className="h-[70vh]">
                <pre className="text-xs whitespace-pre-wrap bg-white/5 p-4 rounded-lg font-mono">
                  {(detail as PromptDetail).prompt_content}
                </pre>
              </ScrollArea>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
