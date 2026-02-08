import { GlassCard } from "@/components/glass/glass-card"
import { Sparkline } from "@/components/charts/sparkline"
import { cn } from "@/lib/utils"

interface KpiCardProps {
  title: string
  value: string | number
  trend?: number[]
  status?: "good" | "warning" | "bad"
  suffix?: string
}

const statusColors = {
  good: "text-emerald-400",
  warning: "text-amber-400",
  bad: "text-red-400",
}

export function KpiCard({ title, value, trend, status = "good", suffix }: KpiCardProps) {
  return (
    <GlassCard className="p-4">
      <p className="text-xs text-muted-foreground mb-1">{title}</p>
      <p className={cn("text-2xl font-bold", statusColors[status])}>
        {value}{suffix}
      </p>
      {trend && trend.length > 0 && (
        <div className="mt-2">
          <Sparkline data={trend} color={status === "good" ? "#10b981" : status === "warning" ? "#f59e0b" : "#ef4444"} height={30} />
        </div>
      )}
    </GlassCard>
  )
}
