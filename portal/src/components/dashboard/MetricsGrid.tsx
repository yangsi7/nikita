import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface MetricsGridProps {
  chapter: number // 1-5
  metrics: {
    intimacy: number // 0-100
    passion: number // 0-100
    trust: number // 0-100
    secureness: number // 0-100
  }
}

interface MetricItemProps {
  name: string
  value: number
  weight: number // For showing relative importance
  description: string
}

function MetricItem({ name, value, weight, description }: MetricItemProps) {
  // Determine color based on value
  const getColor = (val: number): string => {
    if (val >= 70) return 'text-green-500'
    if (val >= 40) return 'text-yellow-500'
    return 'text-red-500'
  }

  const getProgressColor = (val: number): string => {
    if (val >= 70) return 'bg-green-500'
    if (val >= 40) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{name}</CardTitle>
          <span className="text-xs text-muted-foreground">{weight * 100}% weight</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-baseline space-x-2">
          <div className={`text-3xl font-bold ${getColor(value)}`}>{value.toFixed(0)}</div>
          <div className="text-sm text-muted-foreground">/ 100</div>
        </div>
        <Progress value={value} className={`h-2 ${getProgressColor(value)}`} />
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

export function MetricsGrid({ chapter, metrics }: MetricsGridProps) {
  const isHidden = chapter < 2

  if (isHidden) {
    return (
      <div className="space-y-4">
        <h3 className="text-xl font-semibold">Hidden Metrics</h3>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="py-12">
            <div className="text-center space-y-2">
              <div className="text-4xl">🔒</div>
              <p className="text-lg font-medium">Metrics Locked</p>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                These metrics track what Nikita really thinks of you. Reach Chapter 2 to unlock.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold">Hidden Metrics</h3>
        <p className="text-sm text-muted-foreground">What she really thinks</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricItem
          name="Intimacy"
          value={metrics.intimacy}
          weight={0.3}
          description="Emotional closeness and connection"
        />
        <MetricItem
          name="Passion"
          value={metrics.passion}
          weight={0.25}
          description="Romantic and physical attraction"
        />
        <MetricItem
          name="Trust"
          value={metrics.trust}
          weight={0.25}
          description="Reliability and honesty"
        />
        <MetricItem
          name="Secureness"
          value={metrics.secureness}
          weight={0.2}
          description="Emotional safety and stability"
        />
      </div>
      <div className="text-xs text-muted-foreground text-center">
        Relationship Score = (Intimacy × 30%) + (Passion × 25%) + (Trust × 25%) + (Secureness × 20%)
      </div>
    </div>
  )
}
