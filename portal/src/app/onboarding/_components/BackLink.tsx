"use client"

import { ArrowLeft } from "lucide-react"

/**
 * BackLink — left-arrow link on screens 2+; absent on welcome and the
 * first slot screen (entry guard).
 */
export function BackLink({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute top-4 left-4 inline-flex items-center gap-1 text-sm text-foreground/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded px-2 py-1"
    >
      <ArrowLeft className="w-4 h-4" aria-hidden="true" />
      <span>back</span>
    </button>
  )
}
