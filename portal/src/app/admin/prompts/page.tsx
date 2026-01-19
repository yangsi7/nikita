'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useUserPrompts,
  usePromptDetail,
  useLatestPrompt,
  useAdminUsers,
} from '@/hooks/use-admin-data'

export default function PromptsViewingPage() {
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showLatest, setShowLatest] = useState(false)

  const { data: users, isLoading: usersLoading } = useAdminUsers({ page_size: 100 })
  const { data: prompts, isLoading: promptsLoading } = useUserPrompts(selectedUserId)
  const { data: promptDetail, isLoading: detailLoading } = usePromptDetail(selectedPromptId)
  const { data: latestPrompt, isLoading: latestLoading } = useLatestPrompt(
    showLatest ? selectedUserId : null
  )

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
  }

  const formatTokens = (count: number) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`
    }
    return count.toString()
  }

  // Filter users based on search
  const filteredUsers = users?.users.filter(
    (user) =>
      user.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.telegram_id?.toString().includes(searchQuery) ||
      user.id.includes(searchQuery)
  )

  const activePrompt = showLatest ? latestPrompt : promptDetail

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold">Prompt Viewer</h1>
        <p className="text-muted-foreground">
          View generated system prompts for debugging and analysis
        </p>
      </div>

      {/* Main Content - 3 Column Layout */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Users List */}
        <Card>
          <CardHeader>
            <CardTitle>Users</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Search by email, telegram ID, or UUID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-sm"
            />
            <div className="max-h-[500px] overflow-y-auto space-y-2">
              {usersLoading && <p className="text-muted-foreground text-sm">Loading users...</p>}
              {filteredUsers?.length === 0 && (
                <p className="text-muted-foreground text-sm">No users found</p>
              )}
              {filteredUsers?.map((user) => (
                <div
                  key={user.id}
                  className={`p-2 rounded-lg border cursor-pointer transition-colors text-sm ${
                    selectedUserId === user.id
                      ? 'bg-primary/10 border-primary'
                      : 'hover:bg-muted/50'
                  }`}
                  onClick={() => {
                    setSelectedUserId(user.id)
                    setSelectedPromptId(null)
                    setShowLatest(false)
                  }}
                >
                  <div className="font-medium truncate">
                    {user.email || `Telegram ${user.telegram_id}` || user.id.slice(0, 8)}
                  </div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2">
                    <span>Ch {user.chapter}</span>
                    <span className="text-green-500">{user.relationship_score.toFixed(0)}</span>
                    <Badge variant="outline" className="text-xs px-1">
                      {user.game_status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Prompts List */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Prompts</CardTitle>
            {selectedUserId && (
              <Button
                variant={showLatest ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setShowLatest(true)
                  setSelectedPromptId(null)
                }}
              >
                Latest
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3 max-h-[500px] overflow-y-auto">
            {!selectedUserId && (
              <p className="text-muted-foreground text-sm text-center py-8">
                Select a user to view prompts
              </p>
            )}
            {promptsLoading && <p className="text-muted-foreground text-sm">Loading prompts...</p>}
            {selectedUserId && prompts?.items.length === 0 && (
              <p className="text-muted-foreground text-sm">No prompts found for this user</p>
            )}
            {prompts?.items.map((prompt) => (
              <div
                key={prompt.id}
                className={`p-2 rounded-lg border cursor-pointer transition-colors ${
                  selectedPromptId === prompt.id && !showLatest
                    ? 'bg-primary/10 border-primary'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => {
                  setSelectedPromptId(prompt.id)
                  setShowLatest(false)
                }}
              >
                <div className="flex justify-between items-start">
                  <Badge variant="outline" className="text-xs">
                    {prompt.meta_prompt_template}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatTokens(prompt.token_count)} tokens
                  </span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {formatDate(prompt.created_at)}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {prompt.generation_time_ms.toFixed(0)}ms generation time
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Prompt Detail */}
        <Card>
          <CardHeader>
            <CardTitle>
              {showLatest ? 'Latest Prompt' : 'Prompt Detail'}
              {activePrompt?.is_preview && (
                <Badge variant="secondary" className="ml-2">
                  Preview
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-[600px] overflow-y-auto">
            {!activePrompt && !detailLoading && !latestLoading && (
              <p className="text-muted-foreground text-center py-8">
                Select a prompt to view details
              </p>
            )}
            {(detailLoading || latestLoading) && (
              <p className="text-muted-foreground text-center py-8">Loading prompt...</p>
            )}
            {activePrompt && (
              <div className="space-y-4">
                {/* Metadata */}
                <div className="space-y-2 text-sm">
                  {activePrompt.id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">ID:</span>
                      <span className="font-mono text-xs">{activePrompt.id}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Template:</span>
                    <Badge>{activePrompt.meta_prompt_template}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tokens:</span>
                    <span>{activePrompt.token_count.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Generation Time:</span>
                    <span>{activePrompt.generation_time_ms.toFixed(0)}ms</span>
                  </div>
                  {activePrompt.created_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Created:</span>
                      <span>{formatDate(activePrompt.created_at)}</span>
                    </div>
                  )}
                  {activePrompt.conversation_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Conversation:</span>
                      <span className="font-mono text-xs">{activePrompt.conversation_id}</span>
                    </div>
                  )}
                </div>

                {/* Message if present */}
                {activePrompt.message && (
                  <div className="p-3 bg-yellow-500/10 rounded-lg">
                    <p className="text-sm">{activePrompt.message}</p>
                  </div>
                )}

                {/* Context Snapshot */}
                {activePrompt.context_snapshot &&
                  Object.keys(activePrompt.context_snapshot).length > 0 && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Context Snapshot</div>
                      <div className="p-3 bg-muted/30 rounded-lg">
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                          {JSON.stringify(activePrompt.context_snapshot, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                {/* Prompt Content */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Prompt Content</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(activePrompt.prompt_content)
                      }}
                    >
                      Copy
                    </Button>
                  </div>
                  <div className="p-3 bg-muted/30 rounded-lg max-h-[400px] overflow-y-auto">
                    <pre className="text-xs whitespace-pre-wrap font-mono">
                      {activePrompt.prompt_content}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-4">
        Prompts are logged from MetaPromptService.generate_system_prompt()
      </div>
    </div>
  )
}
