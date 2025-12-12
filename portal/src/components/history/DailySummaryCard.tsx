import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { DailySummary } from '@/lib/api/types'

interface DailySummaryCardProps {
  summary: DailySummary
}

const MOOD_EMOJI: Record<string, string> = {
  happy: '😊',
  content: '😌',
  neutral: '😐',
  concerned: '😟',
  upset: '😠',
  sad: '😢',
  excited: '🤩',
  bored: '😴',
}

const MOOD_COLOR: Record<string, string> = {
  happy: 'bg-green-500/10 text-green-500 border-green-500/20',
  content: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  neutral: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
  concerned: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  upset: 'bg-red-500/10 text-red-500 border-red-500/20',
  sad: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  excited: 'bg-pink-500/10 text-pink-500 border-pink-500/20',
  bored: 'bg-gray-400/10 text-gray-400 border-gray-400/20',
}

export function DailySummaryCard({ summary }: DailySummaryCardProps) {
  const moodEmoji = MOOD_EMOJI[summary.mood] || '💭'
  const moodColor = MOOD_COLOR[summary.mood] || 'bg-muted/30 text-muted-foreground border-border/30'

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Daily Summary</CardTitle>
            <CardDescription>
              {new Date(summary.date).toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                year: 'numeric',
              })}
            </CardDescription>
          </div>
          <Badge variant="secondary" className={moodColor}>
            {moodEmoji} {summary.mood}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Nikita's message */}
        <div className="p-4 rounded-md bg-primary/5 border border-primary/10">
          <div className="flex items-start space-x-3">
            <div className="text-2xl">💭</div>
            <div className="flex-1">
              <p className="text-sm font-medium text-primary mb-1">Nikita&apos;s thoughts:</p>
              <p className="text-sm text-foreground/90 leading-relaxed">{summary.summary_text}</p>
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border/30">
          <span>Generated {new Date(summary.created_at).toLocaleDateString()}</span>
          <span>Daily recap</span>
        </div>
      </CardContent>
    </Card>
  )
}
