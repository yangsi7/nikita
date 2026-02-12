"use client"

import { useState } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { ThoughtBubble } from "./thought-bubble"
import { cn } from "@/lib/utils"
import type { ThoughtItem } from "@/lib/api/types"

interface ThoughtFeedProps {
  thoughts: ThoughtItem[]
  onFilterChange?: (type: string | null) => void
}

export function ThoughtFeed({ thoughts, onFilterChange }: ThoughtFeedProps) {
  const [selectedType, setSelectedType] = useState<string | null>(null)

  // Extract unique thought types from the data
  const thoughtTypes = Array.from(
    new Set(thoughts.map((t) => t.thought_type))
  ).sort()

  // Filter thoughts if a type is selected
  const filteredThoughts = selectedType
    ? thoughts.filter((t) => t.thought_type === selectedType)
    : thoughts

  const handleTypeClick = (type: string | null) => {
    setSelectedType(type)
    onFilterChange?.(type)
  }

  if (!thoughts || thoughts.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Nikita hasn&apos;t shared any thoughts yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground mr-1">Filter:</span>
        <Badge
          variant={selectedType === null ? "default" : "outline"}
          className={cn(
            "cursor-pointer transition-colors text-xs",
            selectedType === null
              ? "bg-primary/80 hover:bg-primary"
              : "hover:bg-white/5"
          )}
          onClick={() => handleTypeClick(null)}
        >
          All ({thoughts.length})
        </Badge>
        {thoughtTypes.map((type) => {
          const count = thoughts.filter((t) => t.thought_type === type).length
          const isSelected = selectedType === type

          return (
            <Badge
              key={type}
              variant={isSelected ? "default" : "outline"}
              className={cn(
                "cursor-pointer transition-colors text-xs capitalize",
                isSelected
                  ? "bg-primary/80 hover:bg-primary"
                  : "hover:bg-white/5"
              )}
              onClick={() => handleTypeClick(type)}
            >
              {type.replace(/_/g, " ")} ({count})
            </Badge>
          )
        })}
      </div>

      {/* Total count */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {filteredThoughts.length} thought{filteredThoughts.length !== 1 ? "s" : ""}
          {selectedType && " in this category"}
        </p>
      </div>

      {/* Thought cards */}
      <ScrollArea className="h-[600px]">
        <div className="space-y-3 pr-4">
          {filteredThoughts.map((thought) => (
            <ThoughtBubble key={thought.id} thought={thought} />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
