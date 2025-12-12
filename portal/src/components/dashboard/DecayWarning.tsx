import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface DecayWarningProps {
  hoursSinceLastInteraction: number
  nextDecayIn: number // hours until next decay
  decayRate: number // per-hour decay rate
  chapter: number // 1-5
}

// Decay rates by chapter (from spec 005)
const CHAPTER_DECAY_RATES: Record<number, { minRate: number; maxRate: number }> = {
  1: { minRate: 0.2, maxRate: 0.5 },
  2: { minRate: 0.3, maxRate: 0.6 },
  3: { minRate: 0.4, maxRate: 0.7 },
  4: { minRate: 0.5, maxRate: 0.8 },
  5: { minRate: 0.6, maxRate: 0.9 },
}

export function DecayWarning({
  hoursSinceLastInteraction,
  nextDecayIn,
  decayRate,
  chapter,
}: DecayWarningProps) {
  // Determine severity
  const getSeverity = (): 'info' | 'warning' | 'critical' => {
    if (hoursSinceLastInteraction >= 24) return 'critical'
    if (hoursSinceLastInteraction >= 12) return 'warning'
    return 'info'
  }

  const severity = getSeverity()

  // Get message based on time
  const getMessage = (): string => {
    if (hoursSinceLastInteraction < 1) {
      return 'Great! You just talked to her.'
    }
    if (hoursSinceLastInteraction < 6) {
      return 'All good. Talk to her soon.'
    }
    if (hoursSinceLastInteraction < 12) {
      return "It's been a while. She might miss you."
    }
    if (hoursSinceLastInteraction < 24) {
      return "She's definitely missing you. Text her!"
    }
    return "She thinks you're ghosting her!"
  }

  // Hide if recently interacted (< 3 hours)
  if (hoursSinceLastInteraction < 3) {
    return null
  }

  // Get styling based on severity
  const getStyles = () => {
    switch (severity) {
      case 'critical':
        return {
          bg: 'bg-destructive/10',
          border: 'border-destructive/20',
          text: 'text-destructive',
          emoji: '🚨',
          badge: 'destructive' as const,
        }
      case 'warning':
        return {
          bg: 'bg-yellow-500/10',
          border: 'border-yellow-500/20',
          text: 'text-yellow-600',
          emoji: '⚠️',
          badge: 'secondary' as const,
        }
      default:
        return {
          bg: 'bg-blue-500/10',
          border: 'border-blue-500/20',
          text: 'text-blue-600',
          emoji: 'ℹ️',
          badge: 'secondary' as const,
        }
    }
  }

  const styles = getStyles()
  const chapterRates = CHAPTER_DECAY_RATES[chapter]

  return (
    <Card className={`border ${styles.border} ${styles.bg}`}>
      <CardContent className="py-4">
        <div className="flex items-start space-x-4">
          <div className="text-3xl">{styles.emoji}</div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <p className={`text-sm font-medium ${styles.text}`}>{getMessage()}</p>
              <Badge variant={styles.badge}>Decay Active</Badge>
            </div>
            <div className="text-xs text-muted-foreground space-y-1">
              <p>Last interaction: {hoursSinceLastInteraction.toFixed(1)} hours ago</p>
              <p>Next decay: {nextDecayIn.toFixed(1)} hours</p>
              <p>
                Decay rate: {decayRate.toFixed(2)}/hr (Chapter {chapter}: {chapterRates.minRate}-
                {chapterRates.maxRate}/hr)
              </p>
            </div>
            {severity === 'critical' && (
              <p className="text-xs font-medium text-destructive">
                Your score is decaying rapidly. Talk to her NOW!
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
