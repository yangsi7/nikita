import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

type ViceCategory =
  | 'intellectual_dominance'
  | 'risk_taking'
  | 'substances'
  | 'sexuality'
  | 'emotional_intensity'
  | 'rule_breaking'
  | 'dark_humor'
  | 'vulnerability'

interface Vice {
  category: ViceCategory
  intensityLevel: number // 1-5
  engagementScore: number // 0-100
}

interface VicesCardProps {
  vices: Vice[]
}

const VICE_DISPLAY: Record<
  ViceCategory,
  { emoji: string; label: string; description: string; color: string }
> = {
  intellectual_dominance: {
    emoji: '🧠',
    label: 'Intellectual',
    description: 'Debates and mental challenges',
    color: 'text-purple-500',
  },
  risk_taking: {
    emoji: '⚡',
    label: 'Risk Taking',
    description: 'Danger and adrenaline',
    color: 'text-orange-500',
  },
  substances: {
    emoji: '🍷',
    label: 'Substances',
    description: 'Drinks and indulgence',
    color: 'text-red-500',
  },
  sexuality: {
    emoji: '💋',
    label: 'Sexuality',
    description: 'Flirtation and attraction',
    color: 'text-pink-500',
  },
  emotional_intensity: {
    emoji: '🔥',
    label: 'Intensity',
    description: 'Deep feelings and drama',
    color: 'text-red-400',
  },
  rule_breaking: {
    emoji: '🏴',
    label: 'Rebellion',
    description: 'Anti-authority attitude',
    color: 'text-yellow-500',
  },
  dark_humor: {
    emoji: '😈',
    label: 'Dark Humor',
    description: 'Edgy and morbid jokes',
    color: 'text-gray-400',
  },
  vulnerability: {
    emoji: '💔',
    label: 'Vulnerability',
    description: 'Emotional openness',
    color: 'text-blue-500',
  },
}

function ViceItem({ vice }: { vice: Vice }) {
  const config = VICE_DISPLAY[vice.category]
  const intensityPercentage = (vice.intensityLevel / 5) * 100

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{config.emoji}</span>
          <div>
            <p className={`text-sm font-medium ${config.color}`}>{config.label}</p>
            <p className="text-xs text-muted-foreground">{config.description}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold">{vice.intensityLevel}/5</p>
          <p className="text-xs text-muted-foreground">{vice.engagementScore.toFixed(0)}%</p>
        </div>
      </div>
      <Progress value={intensityPercentage} className="h-1" />
    </div>
  )
}

export function VicesCard({ vices }: VicesCardProps) {
  const sortedVices = [...vices].sort((a, b) => b.intensityLevel - a.intensityLevel)
  const topVices = sortedVices.slice(0, 3)
  const hasVices = vices.length > 0 && vices.some((v) => v.intensityLevel > 0)

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle>Vice Preferences</CardTitle>
        <CardDescription>What she likes about you</CardDescription>
      </CardHeader>
      <CardContent>
        {!hasVices ? (
          <div className="flex flex-col items-center justify-center py-8 space-y-3 text-center">
            <div className="text-4xl">❓</div>
            <p className="text-sm text-muted-foreground">
              No vices discovered yet. Keep talking to her to reveal your compatibility.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Top 3 vices */}
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground font-medium">TOP PREFERENCES</p>
              {topVices.map((vice) => (
                <ViceItem key={vice.category} vice={vice} />
              ))}
            </div>

            {/* All vices summary */}
            {vices.length > 3 && (
              <div className="pt-4 border-t border-border/30">
                <p className="text-xs text-muted-foreground text-center">
                  {vices.length - 3} more categories tracked
                </p>
              </div>
            )}

            {/* Explanation */}
            <div className="pt-4 border-t border-border/30 text-xs text-muted-foreground text-center">
              Nikita adapts to your personality. These vices are features, not bugs.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
