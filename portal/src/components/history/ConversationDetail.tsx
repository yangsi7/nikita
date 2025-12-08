import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Conversation } from '@/lib/api/types'

interface ConversationDetailProps {
  conversation: Conversation
}

export function ConversationDetail({ conversation }: ConversationDetailProps) {
  const duration = conversation.ended_at
    ? (new Date(conversation.ended_at).getTime() - new Date(conversation.started_at).getTime()) /
      1000 /
      60
    : null

  const platformEmoji = conversation.platform === 'telegram' ? '💬' : '🎙️'

  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">{platformEmoji}</span>
            <div>
              <CardTitle>Conversation Details</CardTitle>
              <CardDescription>
                {new Date(conversation.started_at).toLocaleDateString('en-US', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </CardDescription>
            </div>
          </div>
          <Badge variant={conversation.score_change >= 0 ? 'default' : 'destructive'}>
            {conversation.score_change > 0 && '+'}
            {conversation.score_change.toFixed(1)} score
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Started</p>
            <p className="text-sm font-medium">
              {new Date(conversation.started_at).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </div>
          {conversation.ended_at && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Ended</p>
              <p className="text-sm font-medium">
                {new Date(conversation.ended_at).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          )}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="text-sm font-medium">
              {duration ? `${duration.toFixed(0)} min` : 'Ongoing'}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Messages</p>
            <p className="text-sm font-medium">{conversation.message_count}</p>
          </div>
        </div>

        {/* Score Impact */}
        <div className="p-4 rounded-md bg-muted/30 border border-border/30">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium">Score Impact</p>
            <span
              className={`text-lg font-bold ${
                conversation.score_change > 0
                  ? 'text-green-500'
                  : conversation.score_change < 0
                    ? 'text-red-500'
                    : 'text-muted-foreground'
              }`}
            >
              {conversation.score_change > 0 && '+'}
              {conversation.score_change.toFixed(1)}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {conversation.score_change > 0 && 'She enjoyed this conversation'}
            {conversation.score_change < 0 && 'This conversation went poorly'}
            {conversation.score_change === 0 && 'Neutral conversation'}
          </p>
        </div>

        {/* Platform Info */}
        <div className="p-4 rounded-md bg-muted/30 border border-border/30">
          <p className="text-sm font-medium mb-1">Platform</p>
          <p className="text-xs text-muted-foreground capitalize">{conversation.platform}</p>
        </div>

        {/* Note */}
        <div className="pt-4 border-t border-border/30 text-xs text-muted-foreground text-center">
          Message history available soon
        </div>
      </CardContent>
    </Card>
  )
}
