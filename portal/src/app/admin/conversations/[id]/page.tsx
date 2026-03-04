"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import type { PipelineEvent } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { formatDateTime, formatDuration, cn } from "@/lib/utils"
import { STALE_TIMES } from "@/lib/constants"

// ---------------------------------------------------------------------------
// Stage color mapping
// ---------------------------------------------------------------------------

const STAGE_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  extraction:      { bg: "bg-blue-500/15",    text: "text-blue-400",    bar: "bg-blue-500" },
  memory_update:   { bg: "bg-blue-500/15",    text: "text-blue-400",    bar: "bg-blue-400" },
  persistence:     { bg: "bg-blue-500/15",    text: "text-blue-400",    bar: "bg-blue-300" },
  life_simulation: { bg: "bg-purple-500/15",  text: "text-purple-400",  bar: "bg-purple-500" },
  emotional:       { bg: "bg-purple-500/15",  text: "text-purple-400",  bar: "bg-purple-400" },
  emotional_state: { bg: "bg-purple-500/15",  text: "text-purple-400",  bar: "bg-purple-400" },
  game_state:      { bg: "bg-emerald-500/15", text: "text-emerald-400", bar: "bg-emerald-500" },
  conflict:        { bg: "bg-orange-500/15",  text: "text-orange-400",  bar: "bg-orange-500" },
  touchpoint:      { bg: "bg-zinc-500/15",    text: "text-zinc-400",    bar: "bg-zinc-400" },
  summary:         { bg: "bg-zinc-500/15",    text: "text-zinc-400",    bar: "bg-zinc-500" },
  prompt_builder:  { bg: "bg-cyan-500/15",    text: "text-cyan-400",    bar: "bg-cyan-500" },
  orchestrator:    { bg: "bg-zinc-500/15",    text: "text-zinc-300",    bar: "bg-zinc-600" },
}

function stageColor(stage: string | null) {
  return STAGE_COLORS[stage ?? ""] ?? { bg: "bg-zinc-500/15", text: "text-zinc-400", bar: "bg-zinc-500" }
}

// ---------------------------------------------------------------------------
// Event summary line (collapsed view)
// ---------------------------------------------------------------------------

function eventSummary(event: PipelineEvent): string {
  const d = event.data
  switch (event.event_type) {
    case "extraction.complete":
      return `${d.facts_count ?? 0} facts, ${d.threads_count ?? 0} threads, tone: ${d.emotional_tone ?? "—"}`
    case "memory_update.complete":
      return `${d.facts_stored ?? 0} stored, ${d.facts_deduplicated ?? 0} deduped`
    case "persistence.complete":
      return `${d.thoughts_persisted ?? 0} thoughts, ${d.threads_persisted ?? 0} threads persisted`
    case "life_simulation.complete":
      return `${d.events_count ?? 0} life events`
    case "emotional_state.complete": {
      const es = d.emotional_state as Record<string, number> | undefined
      return es ? `valence: ${es.valence?.toFixed?.(2) ?? "—"}, arousal: ${es.arousal?.toFixed?.(2) ?? "—"}` : "emotional state updated"
    }
    case "game_state.complete":
      return `score ${(d.score_delta as number) > 0 ? "+" : ""}${d.score_delta ?? 0}, ch${d.chapter ?? "?"}, changed: ${d.chapter_changed ?? false}`
    case "conflict.complete":
      return `active: ${d.active_conflict ?? false}, temp: ${d.conflict_temperature ?? "—"}`
    case "touchpoint.complete":
      return `scheduled: ${d.touchpoint_scheduled ?? false}`
    case "summary.complete":
      return `updated: ${d.daily_summary_updated ?? false}`
    case "prompt_builder.complete":
      return `${d.prompt_token_count ?? "?"} tokens, platform: ${d.platform ?? "—"}`
    case "pipeline.complete": {
      const stages = d.stages as Array<Record<string, unknown>> | undefined
      return `${stages?.length ?? 0} stages, ${formatDuration(Number(d.total_duration_ms) || 0)}, success: ${d.success ?? "?"}`
    }
    default:
      return event.event_type
  }
}

// ---------------------------------------------------------------------------
// JSON viewer
// ---------------------------------------------------------------------------

function JsonViewer({ data }: { data: Record<string, unknown> }) {
  return (
    <pre className="overflow-x-auto rounded-md bg-black/40 p-3 text-xs leading-relaxed text-zinc-300 font-mono whitespace-pre-wrap break-all">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

// ---------------------------------------------------------------------------
// Summary cards (extracted from pipeline events)
// ---------------------------------------------------------------------------

function SummaryCards({ events }: { events: PipelineEvent[] }) {
  const extraction = events.find((e) => e.event_type === "extraction.complete")
  const memoryUpdate = events.find((e) => e.event_type === "memory_update.complete")
  const gameState = events.find((e) => e.event_type === "game_state.complete")
  const promptBuilder = events.find((e) => e.event_type === "prompt_builder.complete")
  const pipelineComplete = events.find((e) => e.event_type === "pipeline.complete")
  const conflict = events.find((e) => e.event_type === "conflict.complete")

  const cards: { label: string; value: string; color?: string }[] = []

  if (extraction) {
    cards.push({ label: "Facts extracted", value: String(extraction.data.facts_count ?? 0) })
    if (extraction.data.emotional_tone) {
      cards.push({ label: "Emotional tone", value: String(extraction.data.emotional_tone) })
    }
  }
  if (memoryUpdate) {
    cards.push({ label: "Facts stored / deduped", value: `${memoryUpdate.data.facts_stored ?? 0} / ${memoryUpdate.data.facts_deduplicated ?? 0}` })
  }
  if (gameState) {
    const delta = Number(gameState.data.score_delta) || 0
    cards.push({
      label: "Score delta",
      value: `${delta > 0 ? "+" : ""}${delta.toFixed(1)}`,
      color: delta > 0 ? "text-emerald-400" : delta < 0 ? "text-red-400" : "text-zinc-400",
    })
  }
  if (conflict) {
    cards.push({ label: "Conflict temp", value: String(conflict.data.conflict_temperature ?? "—") })
  }
  if (promptBuilder) {
    cards.push({ label: "Prompt tokens", value: String(promptBuilder.data.prompt_token_count ?? "—") })
  }
  if (pipelineComplete) {
    cards.push({ label: "Total duration", value: formatDuration(Number(pipelineComplete.data.total_duration_ms) || 0) })
  }

  if (cards.length === 0) return null

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((c) => (
        <Card key={c.label} className="glass-card border-white/5">
          <CardContent className="p-3">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{c.label}</p>
            <p className={cn("text-lg font-semibold", c.color ?? "text-zinc-100")}>{c.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stage timeline bar
// ---------------------------------------------------------------------------

function StageTimelineBar({ events }: { events: PipelineEvent[] }) {
  const pipelineComplete = events.find((e) => e.event_type === "pipeline.complete")
  if (!pipelineComplete) return null

  const stages = (pipelineComplete.data.stages ?? []) as Array<{
    name: string
    duration_ms: number
    status: string
  }>
  const total = Number(pipelineComplete.data.total_duration_ms) || 1

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">Stage durations (proportional)</p>
      <div className="flex h-6 w-full overflow-hidden rounded-md">
        {stages.map((s) => {
          const pct = Math.max((s.duration_ms / total) * 100, 2)
          const colors = stageColor(s.name)
          const barColor = s.status === "failed" ? "bg-red-500" : s.status === "skipped" ? "bg-zinc-700" : colors.bar
          return (
            <div
              key={s.name}
              className={cn("relative group", barColor)}
              style={{ width: `${pct}%` }}
              title={`${s.name}: ${formatDuration(s.duration_ms)} (${s.status})`}
            >
              <span className="absolute inset-0 flex items-center justify-center text-[9px] font-medium text-white/80 opacity-0 group-hover:opacity-100 transition-opacity truncate px-0.5">
                {s.name}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {stages.map((s) => (
          <span key={s.name} className="text-[10px] text-muted-foreground">
            <span className={cn("inline-block w-2 h-2 rounded-sm mr-1", s.status === "failed" ? "bg-red-500" : stageColor(s.name).bar)} />
            {s.name} {formatDuration(s.duration_ms)}
          </span>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Event timeline
// ---------------------------------------------------------------------------

function EventTimeline({ events }: { events: PipelineEvent[] }) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  function toggle(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-1">
      {events.map((event) => {
        const isExpanded = expandedIds.has(event.id)
        const colors = stageColor(event.stage)
        return (
          <div key={event.id} className="glass-card border-white/5">
            <button
              onClick={() => toggle(event.id)}
              className="flex w-full items-center gap-3 p-3 text-left hover:bg-white/5 transition-colors rounded-md"
            >
              <span className="text-[10px] text-muted-foreground whitespace-nowrap w-16 shrink-0">
                {new Date(event.created_at).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
              <Badge variant="outline" className={cn("text-[10px] shrink-0", colors.text, colors.bg, "border-transparent")}>
                {event.event_type}
              </Badge>
              {event.duration_ms != null && (
                <span className="text-[10px] text-muted-foreground shrink-0">{formatDuration(event.duration_ms)}</span>
              )}
              <span className="text-xs text-zinc-400 truncate flex-1">{eventSummary(event)}</span>
              <span className={cn("text-xs transition-transform", isExpanded ? "rotate-180" : "")}>
                &#9662;
              </span>
            </button>
            {isExpanded && (
              <div className="px-3 pb-3">
                <JsonViewer data={event.data} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ConversationInspectorPage() {
  const params = useParams()
  const id = params.id as string

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "conversation-events", id],
    queryFn: () => adminApi.getConversationEvents(id),
    staleTime: STALE_TIMES.admin,
  })

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={4} />
  if (error) return <ErrorDisplay message="Failed to load conversation events" onRetry={() => refetch()} />

  const events = data?.events ?? []
  const hasEvents = events.length > 0

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/admin">Admin</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbLink href="/admin/text">Conversations</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>{id.slice(0, 8)}</BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Title */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-cyan-400">Conversation Inspector</h1>
        <Badge variant="outline" className="text-xs text-muted-foreground">
          {events.length} event{events.length !== 1 ? "s" : ""}
        </Badge>
      </div>

      {!hasEvents ? (
        /* Graceful degradation for pre-Spec-110 conversations */
        <Card className="glass-card border-white/5">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">
              No pipeline events found for this conversation.
            </p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              Pipeline observability was added in Spec 110. Conversations processed before this update have no event data.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Summary cards */}
          <SummaryCards events={events} />

          {/* Stage timeline bar */}
          <Card className="glass-card border-white/5">
            <CardContent className="p-4">
              <StageTimelineBar events={events} />
            </CardContent>
          </Card>

          {/* Event timeline */}
          <div className="space-y-2">
            <h2 className="text-sm font-medium text-zinc-300">Event Timeline</h2>
            <EventTimeline events={events} />
          </div>
        </>
      )}
    </div>
  )
}
