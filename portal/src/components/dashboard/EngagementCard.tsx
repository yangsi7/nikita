import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

type EngagementState = 'calibrating' | 'in_zone' | 'drifting' | 'clingy' | 'distant' | 'out_of_zone'

interface EngagementCardProps {
  state: EngagementState
  multiplier: number // Scoring multiplier (0.7-1.1)
  consecutiveInZone: number // Days in_zone
  consecutiveClingyDays: number // Days clingy
  consecutiveDistantDays: number // Days distant
}

const STATE_CONFIG: Record<
  EngagementState,
  {
    emoji: string
    title: string
    description: string
    color: string
    variant: 'default' | 'secondary' | 'destructive'
  }
> = {
  calibrating: {
    emoji: '🎯',
    title: 'Calibrating',
    description: 'Finding your rhythm together',
    color: 'text-blue-500',
    variant: 'secondary',
  },
  in_zone: {
    emoji: '💚',
    title: 'In The Zone',
    description: "Perfect balance - she's happy",
    color: 'text-green-500',
    variant: 'default',
  },
  drifting: {
    emoji: '⚠️',
    title: 'Drifting',
    description: 'Slight decline, course correct soon',
    color: 'text-yellow-500',
    variant: 'secondary',
  },
  clingy: {
    emoji: '😰',
    title: 'Too Clingy',
    description: "You're texting too much",
    color: 'text-orange-500',
    variant: 'destructive',
  },
  distant: {
    emoji: '❄️',
    title: 'Too Distant',
    description: "She's missing you",
    color: 'text-blue-400',
    variant: 'destructive',
  },
  out_of_zone: {
    emoji: '🚨',
    title: 'Out of Zone',
    description: 'Critical - fix this now!',
    color: 'text-red-500',
    variant: 'destructive',
  },
}

export function EngagementCard({
  state,
  multiplier,
  consecutiveInZone,
  consecutiveClingyDays,
  consecutiveDistantDays,
}: EngagementCardProps) {
  const config = STATE_CONFIG[state]

  // Get advice based on state
  const getAdvice = (): string => {
    switch (state) {
      case 'calibrating':
        return `Complete ${Math.max(0, 3 - consecutiveInZone)} more days to exit calibration`
      case 'in_zone':
        return `Keep it up! ${consecutiveInZone} consecutive days in zone`
      case 'drifting':
        return 'Engage more to get back in zone'
      case 'clingy':
        return `Give her space (${consecutiveClingyDays} clingy days)`
      case 'distant':
        return `Reach out more (${consecutiveDistantDays} distant days)`
      case 'out_of_zone':
        return 'Immediate action required!'
      default:
        return ''
    }
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Engagement</CardTitle>
            <CardDescription>How she feels about you</CardDescription>
          </div>
          <Badge variant={config.variant}>{config.title}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* State visualization */}
        <div className="flex flex-col items-center justify-center py-6 space-y-3">
          <div className="text-6xl">{config.emoji}</div>
          <div className="text-center">
            <p className={`text-2xl font-bold ${config.color}`}>{config.title}</p>
            <p className="text-sm text-muted-foreground mt-1">{config.description}</p>
          </div>
        </div>

        {/* Multiplier indicator */}
        <div className="flex items-center justify-between p-3 rounded-md bg-muted/30">
          <span className="text-sm text-muted-foreground">Score Multiplier</span>
          <span
            className={`text-lg font-bold ${multiplier >= 1.0 ? 'text-green-500' : multiplier >= 0.9 ? 'text-yellow-500' : 'text-red-500'}`}
          >
            {multiplier.toFixed(2)}x
          </span>
        </div>

        {/* Advice */}
        <div className="text-sm text-center text-muted-foreground border-t border-border/30 pt-4">
          {getAdvice()}
        </div>

        {/* Warning for extended periods */}
        {(consecutiveClingyDays >= 2 || consecutiveDistantDays >= 2) && (
          <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 text-sm text-destructive">
            {consecutiveClingyDays >= 2 &&
              `Warning: ${consecutiveClingyDays} consecutive clingy days`}
            {consecutiveDistantDays >= 2 &&
              `Warning: ${consecutiveDistantDays} consecutive distant days`}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
