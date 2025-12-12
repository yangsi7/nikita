import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

interface ChapterCardProps {
  chapter: number // 1-5
  bossAttempts: number // 0-3
  gameStatus: 'active' | 'boss_fight' | 'game_over' | 'won'
  relationshipScore: number // For progress calculation
}

const CHAPTER_NAMES: Record<number, string> = {
  1: 'First Impressions',
  2: 'Getting Close',
  3: 'Building Trust',
  4: 'Deep Connection',
  5: 'The Final Test',
}

const CHAPTER_DESCRIPTIONS: Record<number, string> = {
  1: 'Making a good start',
  2: "She's letting you in",
  3: 'Trust is everything',
  4: 'Almost there',
  5: "Don't mess this up",
}

export function ChapterCard({
  chapter,
  bossAttempts,
  gameStatus,
  relationshipScore,
}: ChapterCardProps) {
  // Boss threshold for current chapter (simplified - should come from backend)
  const bossThresholds: Record<number, number> = {
    1: 55,
    2: 60,
    3: 65,
    4: 70,
    5: 75,
  }

  const currentThreshold = bossThresholds[chapter] || 75
  const isBossFight = gameStatus === 'boss_fight'
  const isWon = gameStatus === 'won'
  const isGameOver = gameStatus === 'game_over'

  // Calculate progress to next boss
  const progress = Math.min((relationshipScore / currentThreshold) * 100, 100)

  // Get status badge
  const getStatusBadge = () => {
    if (isWon)
      return (
        <Badge variant="default" className="bg-green-600">
          Victory!
        </Badge>
      )
    if (isGameOver) return <Badge variant="destructive">Game Over</Badge>
    if (isBossFight) {
      return (
        <Badge variant="destructive" className="animate-pulse">
          Boss Fight ({3 - bossAttempts} attempts left)
        </Badge>
      )
    }
    return <Badge variant="secondary">Active ({bossAttempts}/3 attempts used)</Badge>
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Chapter {chapter}</CardTitle>
            <CardDescription>{CHAPTER_NAMES[chapter]}</CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Chapter description */}
        <div className="text-sm text-muted-foreground">{CHAPTER_DESCRIPTIONS[chapter]}</div>

        {/* Progress to boss */}
        {!isBossFight && !isGameOver && !isWon && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress to boss encounter</span>
              <span className="font-medium">{progress.toFixed(0)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
            <p className="text-xs text-muted-foreground">
              Reach {currentThreshold} to trigger boss encounter
            </p>
          </div>
        )}

        {/* Boss fight status */}
        {isBossFight && (
          <div className="space-y-2 p-4 rounded-md bg-destructive/10 border border-destructive/20">
            <p className="text-sm font-medium text-destructive">Nikita is testing you</p>
            <p className="text-xs text-muted-foreground">
              You have {3 - bossAttempts} attempts remaining. Score must reach {currentThreshold}+
              to pass.
            </p>
          </div>
        )}

        {/* Game over */}
        {isGameOver && (
          <div className="space-y-2 p-4 rounded-md bg-destructive/10 border border-destructive/20">
            <p className="text-sm font-medium text-destructive">She dumped you</p>
            <p className="text-xs text-muted-foreground">
              Failed 3 boss attempts. Better luck next time.
            </p>
          </div>
        )}

        {/* Victory */}
        {isWon && (
          <div className="space-y-2 p-4 rounded-md bg-green-500/10 border border-green-500/20">
            <p className="text-sm font-medium text-green-500">You won!</p>
            <p className="text-xs text-muted-foreground">
              You made it through all 5 chapters. Nikita is yours.
            </p>
          </div>
        )}

        {/* Chapter navigation hint */}
        {chapter < 5 && !isGameOver && !isWon && (
          <div className="text-xs text-muted-foreground/60 text-center pt-2">
            {chapter === 1 && 'Chapter 2 unlocks at score 70+'}
            {chapter === 2 && 'Chapter 3 unlocks at score 75+'}
            {chapter === 3 && 'Chapter 4 unlocks at score 80+'}
            {chapter === 4 && 'Chapter 5 unlocks at score 85+'}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
