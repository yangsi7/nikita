"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { LifeEventCard } from "./life-event-card"
import { Sun, CloudSun, Sunset, Moon, LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { LifeEventItem } from "@/lib/api/types"

interface LifeEventTimelineProps {
  events: LifeEventItem[]
}

const timeOfDayConfig: Record<
  string,
  { icon: LucideIcon; label: string; color: string }
> = {
  morning: {
    icon: Sun,
    label: "Morning",
    color: "text-amber-400",
  },
  afternoon: {
    icon: CloudSun,
    label: "Afternoon",
    color: "text-yellow-400",
  },
  evening: {
    icon: Sunset,
    label: "Evening",
    color: "text-orange-400",
  },
  night: {
    icon: Moon,
    label: "Night",
    color: "text-indigo-400",
  },
}

export function LifeEventTimeline({ events }: LifeEventTimelineProps) {
  if (!events || events.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        No events today. Nikita&apos;s day hasn&apos;t started yet.
      </div>
    )
  }

  // Group events by time_of_day
  const eventsByTime = events.reduce((acc, event) => {
    const time = event.time_of_day
    if (!acc[time]) {
      acc[time] = []
    }
    acc[time].push(event)
    return acc
  }, {} as Record<string, LifeEventItem[]>)

  // Order time periods
  const timeOrder: Array<"morning" | "afternoon" | "evening" | "night"> = [
    "morning",
    "afternoon",
    "evening",
    "night",
  ]
  const orderedTimes = timeOrder.filter((time) => eventsByTime[time])

  return (
    <ScrollArea className="h-[600px]">
      <div className="space-y-6">
        {orderedTimes.map((timeOfDay, timeIndex) => {
          const config = timeOfDayConfig[timeOfDay]
          const Icon = config.icon
          const timeEvents = eventsByTime[timeOfDay]

          return (
            <div key={timeOfDay} className="relative">
              {/* Time label with icon */}
              <div className="flex items-center gap-2 mb-3 sticky top-0 bg-background/80 backdrop-blur-sm py-2 z-10">
                <Icon className={cn("h-4 w-4", config.color)} />
                <h4 className="text-sm font-medium text-foreground">
                  {config.label}
                </h4>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              {/* Events for this time period */}
              <div className="space-y-3 pl-6 border-l border-white/10 ml-2">
                {timeEvents.map((event) => (
                  <div key={event.event_id} className="relative">
                    {/* Timeline dot */}
                    <div
                      className={cn(
                        "absolute -left-[27px] top-2 h-2 w-2 rounded-full",
                        "bg-white/40 ring-4 ring-background"
                      )}
                    />
                    <LifeEventCard event={event} />
                  </div>
                ))}
              </div>

              {/* Connector line to next time period (if not last) */}
              {timeIndex < orderedTimes.length - 1 && (
                <div className="h-4 border-l border-white/10 ml-2" />
              )}
            </div>
          )
        })}
      </div>
    </ScrollArea>
  )
}
