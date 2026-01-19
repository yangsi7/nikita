'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  useTextConversations,
  useTextStats,
  useTextConversationDetail,
  usePipelineStatus,
} from '@/hooks/use-admin-data'

export default function TextMonitoringPage() {
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null)
  const [showPipeline, setShowPipeline] = useState(false)

  const { data: stats, isLoading: statsLoading } = useTextStats()
  const { data: conversations, isLoading: convsLoading } = useTextConversations()
  const { data: convDetail } = useTextConversationDetail(selectedConvId)
  const { data: pipelineStatus } = usePipelineStatus(showPipeline ? selectedConvId : null)

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  // Pipeline stage names for the 9-stage post-processor
  const PIPELINE_STAGES = [
    { number: 1, name: 'Ingestion' },
    { number: 2, name: 'Extraction' },
    { number: 3, name: 'Analysis' },
    { number: 4, name: 'Threads' },
    { number: 5, name: 'Thoughts' },
    { number: 6, name: 'Graph Updates' },
    { number: 7, name: 'Summary Rollups' },
    { number: 8, name: 'Vice Processing' },
    { number: 9, name: 'Finalization' },
  ]

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold">Text Monitoring</h1>
        <p className="text-muted-foreground">
          Monitor Telegram text conversations and post-processing pipeline
        </p>
      </div>

      {/* Stats Overview */}
      {!statsLoading && stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Convos (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-500">
                {stats.total_conversations_24h}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Messages (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total_messages_24h}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Convos (7d)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total_conversations_7d}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Boss Fights (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-500">{stats.boss_fights_24h}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Msgs/Conv
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {stats.avg_messages_per_conversation?.toFixed(1) || '-'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Processing Stats */}
      {!statsLoading && stats && Object.keys(stats.processing_stats).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats.processing_stats).map(([status, count]) => (
                <Badge
                  key={status}
                  variant={
                    status === 'processed'
                      ? 'default'
                      : status === 'active'
                        ? 'secondary'
                        : status === 'failed'
                          ? 'destructive'
                          : 'outline'
                  }
                  className="px-3 py-1 text-sm"
                >
                  {status}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Conversations List */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Text Conversations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[600px] overflow-y-auto">
            {convsLoading && <p className="text-muted-foreground">Loading...</p>}
            {conversations?.items.length === 0 && (
              <p className="text-muted-foreground">No text conversations found</p>
            )}
            {conversations?.items.map((conv) => (
              <div
                key={conv.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedConvId === conv.id ? 'bg-primary/10 border-primary' : 'hover:bg-muted/50'
                }`}
                onClick={() => {
                  setSelectedConvId(conv.id)
                  setShowPipeline(false)
                }}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{conv.user_name || 'Unknown User'}</span>
                      {conv.is_boss_fight && (
                        <Badge variant="destructive" className="text-xs">
                          BOSS
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(conv.started_at)}
                    </div>
                  </div>
                  <Badge
                    variant={
                      conv.status === 'processed'
                        ? 'default'
                        : conv.status === 'active'
                          ? 'secondary'
                          : conv.status === 'failed'
                            ? 'destructive'
                            : 'outline'
                    }
                  >
                    {conv.status}
                  </Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>{conv.message_count} msgs</span>
                  {conv.chapter_at_time && <span>Ch {conv.chapter_at_time}</span>}
                  {conv.score_delta !== null && (
                    <span className={conv.score_delta >= 0 ? 'text-green-500' : 'text-red-500'}>
                      {conv.score_delta >= 0 ? '+' : ''}
                      {conv.score_delta.toFixed(1)}
                    </span>
                  )}
                  {conv.emotional_tone && <span className="italic">{conv.emotional_tone}</span>}
                </div>
                {conv.conversation_summary && (
                  <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
                    {conv.conversation_summary}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Detail Panel */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Conversation Detail</CardTitle>
            {selectedConvId && (
              <Button
                variant={showPipeline ? 'default' : 'outline'}
                size="sm"
                onClick={() => setShowPipeline(!showPipeline)}
              >
                {showPipeline ? 'Show Messages' : 'Show Pipeline'}
              </Button>
            )}
          </CardHeader>
          <CardContent className="max-h-[600px] overflow-y-auto">
            {!selectedConvId && (
              <p className="text-muted-foreground text-center py-8">
                Select a conversation to view details
              </p>
            )}

            {/* Pipeline Status View */}
            {selectedConvId && showPipeline && pipelineStatus && (
              <div className="space-y-4">
                {/* Pipeline Overview */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <Badge>{pipelineStatus.status}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Attempts:</span>
                    <span>{pipelineStatus.processing_attempts}</span>
                  </div>
                  {pipelineStatus.processed_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Processed At:</span>
                      <span>{formatDate(pipelineStatus.processed_at)}</span>
                    </div>
                  )}
                </div>

                {/* Results Summary */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-muted/30 rounded text-center">
                    <div className="text-xl font-bold">{pipelineStatus.threads_created}</div>
                    <div className="text-xs text-muted-foreground">Threads</div>
                  </div>
                  <div className="p-2 bg-muted/30 rounded text-center">
                    <div className="text-xl font-bold">{pipelineStatus.thoughts_created}</div>
                    <div className="text-xs text-muted-foreground">Thoughts</div>
                  </div>
                  <div className="p-2 bg-muted/30 rounded text-center">
                    <div className="text-xl font-bold">{pipelineStatus.entities_extracted}</div>
                    <div className="text-xs text-muted-foreground">Entities</div>
                  </div>
                </div>

                {/* Pipeline Stages */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">Pipeline Stages</div>
                  {PIPELINE_STAGES.map((stage) => {
                    const stageData = pipelineStatus.stages.find(
                      (s) => s.stage_number === stage.number
                    )
                    const isComplete = stageData?.completed || false
                    return (
                      <div key={stage.number} className="flex items-center gap-2">
                        <div
                          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                            isComplete
                              ? 'bg-green-500 text-white'
                              : 'bg-muted text-muted-foreground'
                          }`}
                        >
                          {isComplete ? '✓' : stage.number}
                        </div>
                        <div className="flex-1">
                          <div className="text-sm">{stage.name}</div>
                          {stageData?.result_summary && (
                            <div className="text-xs text-muted-foreground">
                              {stageData.result_summary}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Progress Bar */}
                <div>
                  <Progress
                    value={
                      (pipelineStatus.stages.filter((s) => s.completed).length /
                        PIPELINE_STAGES.length) *
                      100
                    }
                    className="h-2"
                  />
                  <div className="text-xs text-muted-foreground text-center mt-1">
                    {pipelineStatus.stages.filter((s) => s.completed).length} of{' '}
                    {PIPELINE_STAGES.length} stages complete
                  </div>
                </div>
              </div>
            )}

            {/* Messages View */}
            {selectedConvId && !showPipeline && convDetail && (
              <div className="space-y-4">
                {/* Metadata */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">User:</span>
                    <span>{convDetail.user_name || convDetail.user_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Started:</span>
                    <span>{formatDate(convDetail.started_at)}</span>
                  </div>
                  {convDetail.ended_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Ended:</span>
                      <span>{formatDate(convDetail.ended_at)}</span>
                    </div>
                  )}
                  {convDetail.is_boss_fight && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Type:</span>
                      <Badge variant="destructive">Boss Fight</Badge>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Attempts:</span>
                    <span>{convDetail.processing_attempts}</span>
                  </div>
                </div>

                {/* Summary */}
                {convDetail.conversation_summary && (
                  <div className="p-3 bg-muted/30 rounded-lg">
                    <div className="text-xs font-medium text-muted-foreground mb-1">Summary</div>
                    <p className="text-sm">{convDetail.conversation_summary}</p>
                  </div>
                )}

                {/* Emotional Tone */}
                {convDetail.emotional_tone && (
                  <div className="p-3 bg-muted/30 rounded-lg">
                    <div className="text-xs font-medium text-muted-foreground mb-1">
                      Emotional Tone
                    </div>
                    <p className="text-sm">{convDetail.emotional_tone}</p>
                  </div>
                )}

                {/* Extracted Entities */}
                {convDetail.extracted_entities &&
                  Object.keys(convDetail.extracted_entities).length > 0 && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <div className="text-xs font-medium text-muted-foreground mb-1">
                        Extracted Entities
                      </div>
                      <pre className="text-xs overflow-x-auto">
                        {JSON.stringify(convDetail.extracted_entities, null, 2)}
                      </pre>
                    </div>
                  )}

                {/* Messages */}
                <div className="space-y-2">
                  <div className="text-sm font-medium">Messages ({convDetail.message_count})</div>
                  {convDetail.messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded text-sm ${
                        msg.role === 'user' ? 'bg-blue-500/10 ml-4' : 'bg-primary/10 mr-4'
                      }`}
                    >
                      <div className="flex justify-between">
                        <span className="text-xs font-medium capitalize">{msg.role}</span>
                        {msg.timestamp && (
                          <span className="text-xs text-muted-foreground">{msg.timestamp}</span>
                        )}
                      </div>
                      <div className="mt-1">{msg.content}</div>
                      {msg.analysis && (
                        <div className="mt-2 p-2 bg-muted/50 rounded text-xs">
                          <pre className="overflow-x-auto">
                            {JSON.stringify(msg.analysis, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-4">
        Data refreshes every 30 seconds
      </div>
    </div>
  )
}
