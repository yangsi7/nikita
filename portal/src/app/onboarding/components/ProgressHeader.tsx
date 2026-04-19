"use client"

/**
 * ProgressHeader — Spec 214 T3.8.
 *
 * Top bar showing "Building your file... N%" with a bar-width map to the
 * server-owned `progress_pct`. AC-T3.8.2: the client never re-derives the
 * percentage; it renders what the server sent verbatim.
 */

export interface ProgressHeaderProps {
  progressPct: number
}

export function ProgressHeader({ progressPct }: ProgressHeaderProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(progressPct)))
  return (
    <div
      data-testid="progress-header"
      className="w-full border-b bg-background px-4 py-3"
    >
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span data-testid="progress-label">Building your file... {clamped}%</span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          data-testid="progress-bar"
          className="h-full bg-primary transition-all"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}
