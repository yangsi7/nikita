import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ScoreCardProps {
  score: number // 0-100
  previousScore?: number // For trend calculation
  chapter: number // 1-5
}

export function ScoreCard({ score, previousScore, chapter }: ScoreCardProps) {
  // Calculate trend
  const trend =
    previousScore !== undefined
      ? score > previousScore
        ? 'increasing'
        : score < previousScore
          ? 'decreasing'
          : 'stable'
      : 'stable'

  // Determine color based on score
  const getScoreColor = (score: number): string => {
    if (score >= 70) return 'text-green-500'
    if (score >= 40) return 'text-yellow-500'
    return 'text-red-500'
  }

  // Get stroke color for circle
  const getStrokeColor = (score: number): string => {
    if (score >= 70) return 'stroke-green-500'
    if (score >= 40) return 'stroke-yellow-500'
    return 'stroke-red-500'
  }

  // Get badge variant
  const getBadgeVariant = () => {
    if (trend === 'increasing') return 'default' // Will show primary color (red)
    if (trend === 'decreasing') return 'destructive'
    return 'secondary'
  }

  // Calculate circle progress (percentage of circumference)
  const radius = 80
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Relationship Score</CardTitle>
            <CardDescription>Chapter {chapter} standing</CardDescription>
          </div>
          <Badge variant={getBadgeVariant()}>
            {trend === 'increasing' && '↑ Rising'}
            {trend === 'decreasing' && '↓ Falling'}
            {trend === 'stable' && '→ Stable'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col items-center justify-center">
        {/* Circular Progress */}
        <div className="relative w-48 h-48">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
            {/* Background circle */}
            <circle
              cx="100"
              cy="100"
              r={radius}
              stroke="currentColor"
              strokeWidth="12"
              fill="none"
              className="text-muted/20"
            />
            {/* Progress circle */}
            <circle
              cx="100"
              cy="100"
              r={radius}
              stroke="currentColor"
              strokeWidth="12"
              fill="none"
              className={getStrokeColor(score)}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              style={{
                transition: 'stroke-dashoffset 0.5s ease',
              }}
            />
          </svg>
          {/* Score text in center */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className={`text-6xl font-bold ${getScoreColor(score)}`}>{score.toFixed(0)}</div>
            <div className="text-sm text-muted-foreground">out of 100</div>
          </div>
        </div>

        {/* Score interpretation */}
        <div className="mt-4 text-center">
          <p className="text-sm text-muted-foreground">
            {score >= 70 && "She's into you"}
            {score >= 40 && score < 70 && 'Keep her interested'}
            {score < 40 && "You're losing her"}
          </p>
          {previousScore !== undefined && (
            <p className="text-xs text-muted-foreground/60 mt-1">
              {trend === 'increasing' && `+${(score - previousScore).toFixed(1)} from last time`}
              {trend === 'decreasing' && `${(score - previousScore).toFixed(1)} from last time`}
              {trend === 'stable' && 'No change from last time'}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
