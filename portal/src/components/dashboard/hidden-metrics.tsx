"use client"

import { RadarMetrics } from "@/components/charts/radar-metrics"
import type { UserMetrics } from "@/lib/api/types"

interface HiddenMetricsProps {
  metrics: UserMetrics
}

export function HiddenMetrics({ metrics }: HiddenMetricsProps) {
  return <RadarMetrics metrics={metrics} />
}
