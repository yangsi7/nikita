import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Conversation } from '@/lib/api/types'

interface ConversationListProps {
  conversations: Conversation[]
  onSelectConversation?: (id: string) => void
}

function ConversationItem({
  conversation,
  onClick,
}: {
  conversation: Conversation
  onClick?: () => void
}) {
  const duration = conversation.ended_at
    ? (new Date(conversation.ended_at).getTime() - new Date(conversation.started_at).getTime()) /
      1000 /
      60
    : null

  const platformEmoji = conversation.platform === 'telegram' ? '💬' : '🎙️'

  return (
    <Card
      className="border-border/50 bg-card/50 hover:bg-card/70 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <CardContent className="py-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className="text-2xl">{platformEmoji}</div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center space-x-2">
                <p className="text-sm font-medium">
                  {new Date(conversation.started_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(conversation.started_at).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                <span>{conversation.message_count} messages</span>
                {duration !== null && <span>• {duration.toFixed(0)} min</span>}
                <span>• {conversation.platform}</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <Badge variant={conversation.score_change >= 0 ? 'default' : 'destructive'}>
              {conversation.score_change > 0 && '+'}
              {conversation.score_change.toFixed(1)}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function ConversationList({ conversations, onSelectConversation }: ConversationListProps) {
  if (conversations.length === 0) {
    return (
      <Card className="border-border/50 bg-card/50">
        <CardContent className="py-12">
          <div className="text-center space-y-3">
            <div className="text-4xl">💭</div>
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <p className="text-xs text-muted-foreground/60">
              Start chatting with Nikita on Telegram to see your history here
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold">Conversation History</h3>
          <p className="text-sm text-muted-foreground">{conversations.length} conversations</p>
        </div>
      </div>
      <div className="space-y-3">
        {conversations.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            onClick={() => onSelectConversation?.(conversation.id)}
          />
        ))}
      </div>
    </div>
  )
}
