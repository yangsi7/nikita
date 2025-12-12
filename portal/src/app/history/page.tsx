'use client'

import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/supabase/client'
import { useUserStats } from '@/hooks/use-dashboard-data'
import { ScoreHistoryGraph } from '@/components/history/ScoreHistoryGraph'
import { DailySummaryCard } from '@/components/history/DailySummaryCard'
import { Card, CardContent } from '@/components/ui/card'
import { apiClient } from '@/lib/api/client'
import { useQuery } from '@tanstack/react-query'
import { Navigation } from '@/components/layout/Navigation'

export default function HistoryPage() {
  const router = useRouter()
  const { data: stats } = useUserStats()
  const { data: scoreHistoryResponse } = useQuery({
    queryKey: ['scoreHistory'],
    queryFn: () => apiClient.getScoreHistory(30),
    staleTime: 60 * 1000, // 60 seconds
  })
  const scoreHistory = scoreHistoryResponse?.points ?? []

  const todayDate = new Date().toISOString().split('T')[0]
  const { data: todaySummary } = useQuery({
    queryKey: ['dailySummary', todayDate],
    queryFn: () => apiClient.getDailySummary(todayDate),
    enabled: !!todayDate,
    retry: false, // Don't retry if summary doesn't exist yet
  })

  const handleLogout = async () => {
    await logout()
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
              Nikita
            </h1>
            <Navigation />
          </div>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            Sign Out
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Page Title */}
        <div>
          <h2 className="text-3xl font-bold mb-2">Score & Summary History</h2>
          <p className="text-muted-foreground">Track your relationship journey over time</p>
        </div>

        {/* Score History Graph */}
        <ScoreHistoryGraph history={scoreHistory} currentChapter={stats?.chapter || 1} />

        {/* Today's Summary */}
        {todaySummary && (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">Today&apos;s Summary</h3>
            <DailySummaryCard summary={todaySummary} />
          </div>
        )}

        {/* No summary message */}
        {!todaySummary && (
          <Card className="border-border/50 bg-card/50">
            <CardContent className="py-12">
              <div className="text-center space-y-3">
                <div className="text-4xl">📝</div>
                <p className="text-sm text-muted-foreground">No summary for today yet</p>
                <p className="text-xs text-muted-foreground/60">
                  Summaries are generated at the end of each day
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
