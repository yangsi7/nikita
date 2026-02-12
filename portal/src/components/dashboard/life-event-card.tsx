"use client"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import {
  Briefcase,
  Users,
  User,
  Palette,
  Heart,
  LucideIcon,
} from "lucide-react"
import type { LifeEventItem } from "@/lib/api/types"

interface LifeEventCardProps {
  event: LifeEventItem
}

const domainConfig: Record<
  string,
  { icon: LucideIcon; borderColor: string; iconColor: string }
> = {
  work: {
    icon: Briefcase,
    borderColor: "border-blue-400/50",
    iconColor: "text-blue-400",
  },
  social: {
    icon: Users,
    borderColor: "border-emerald-400/50",
    iconColor: "text-emerald-400",
  },
  personal: {
    icon: User,
    borderColor: "border-purple-400/50",
    iconColor: "text-purple-400",
  },
  creative: {
    icon: Palette,
    borderColor: "border-amber-400/50",
    iconColor: "text-amber-400",
  },
  health: {
    icon: Heart,
    borderColor: "border-rose-400/50",
    iconColor: "text-rose-400",
  },
}

const defaultConfig = {
  icon: User,
  borderColor: "border-slate-400/50",
  iconColor: "text-slate-400",
}

const timeOfDayLabels: Record<string, string> = {
  morning: "Morning",
  afternoon: "Afternoon",
  evening: "Evening",
  night: "Night",
}

export function LifeEventCard({ event }: LifeEventCardProps) {
  const config = domainConfig[event.domain] ?? defaultConfig
  const Icon = config.icon
  const opacity = event.importance < 0.3 ? "opacity-60" : "opacity-100"

  return (
    <div
      className={cn(
        "rounded-lg bg-white/5 border border-white/10 p-3 transition-opacity",
        "border-l-2",
        config.borderColor,
        opacity
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Icon className={cn("h-4 w-4", config.iconColor)} />
          <span className="text-xs text-muted-foreground capitalize">
            {event.domain}
          </span>
        </div>
        <span className="text-xs text-muted-foreground/60">
          {timeOfDayLabels[event.time_of_day] ?? event.time_of_day}
        </span>
      </div>

      <p className="text-sm text-foreground leading-relaxed">
        {event.description}
      </p>

      {event.entities && event.entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {event.entities.map((entity, i) => (
            <Badge key={i} variant="outline" className="text-xs px-2 py-0.5">
              {entity}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
