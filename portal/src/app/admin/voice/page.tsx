'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  useVoiceConversations,
  useVoiceStats,
  useElevenLabsCalls,
  useVoiceConversationDetail,
  useElevenLabsCallDetail,
} from '@/hooks/use-admin-data'

export default function VoiceMonitoringPage() {
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null)
  const [selectedElevenLabsId, setSelectedElevenLabsId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'db' | 'elevenlabs'>('db')

  const { data: stats, isLoading: statsLoading } = useVoiceStats()
  const { data: conversations, isLoading: convsLoading } = useVoiceConversations()
  const { data: elevenLabsCalls, isLoading: callsLoading } = useElevenLabsCalls()
  const { data: convDetail } = useVoiceConversationDetail(selectedConvId)
  const { data: callDetail } = useElevenLabsCallDetail(selectedElevenLabsId)

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  const formatUnixTime = (unix: number) => {
    return new Date(unix * 1000).toLocaleString()
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold">Voice Monitoring</h1>
        <p className="text-muted-foreground">
          Monitor voice calls from database and ElevenLabs API
        </p>
      </div>

      {/* Stats Overview */}
      {!statsLoading && stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Calls (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-500">{stats.total_calls_24h}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Calls (7d)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total_calls_7d}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Calls (30d)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total_calls_30d}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Duration
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {formatDuration(stats.avg_call_duration_secs)}
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

      {/* Tab Selector */}
      <div className="flex space-x-2">
        <Button
          variant={activeTab === 'db' ? 'default' : 'outline'}
          onClick={() => {
            setActiveTab('db')
            setSelectedElevenLabsId(null)
          }}
        >
          Database Conversations
        </Button>
        <Button
          variant={activeTab === 'elevenlabs' ? 'default' : 'outline'}
          onClick={() => {
            setActiveTab('elevenlabs')
            setSelectedConvId(null)
          }}
        >
          ElevenLabs API
        </Button>
      </div>

      {/* Database Conversations Tab */}
      {activeTab === 'db' && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Conversations List */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Voice Conversations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[600px] overflow-y-auto">
              {convsLoading && <p className="text-muted-foreground">Loading...</p>}
              {conversations?.items.length === 0 && (
                <p className="text-muted-foreground">No voice conversations found</p>
              )}
              {conversations?.items.map((conv) => (
                <div
                  key={conv.id}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedConvId === conv.id
                      ? 'bg-primary/10 border-primary'
                      : 'hover:bg-muted/50'
                  }`}
                  onClick={() => setSelectedConvId(conv.id)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium">{conv.user_name || 'Unknown User'}</div>
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
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Conversation Detail */}
          <Card>
            <CardHeader>
              <CardTitle>Conversation Detail</CardTitle>
            </CardHeader>
            <CardContent className="max-h-[600px] overflow-y-auto">
              {!selectedConvId && (
                <p className="text-muted-foreground text-center py-8">
                  Select a conversation to view details
                </p>
              )}
              {convDetail && (
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
                    {convDetail.elevenlabs_session_id && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">ElevenLabs ID:</span>
                        <span className="font-mono text-xs">
                          {convDetail.elevenlabs_session_id}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Summary */}
                  {convDetail.conversation_summary && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <div className="text-xs font-medium text-muted-foreground mb-1">Summary</div>
                      <p className="text-sm">{convDetail.conversation_summary}</p>
                    </div>
                  )}

                  {/* Transcript */}
                  <div className="space-y-2">
                    <div className="text-sm font-medium">
                      Transcript ({convDetail.message_count} messages)
                    </div>
                    {convDetail.messages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`p-2 rounded text-sm ${
                          msg.role === 'user' ? 'bg-blue-500/10 ml-4' : 'bg-primary/10 mr-4'
                        }`}
                      >
                        <div className="text-xs font-medium capitalize mb-1">{msg.role}</div>
                        <div>{msg.content}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ElevenLabs API Tab */}
      {activeTab === 'elevenlabs' && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Calls List */}
          <Card>
            <CardHeader>
              <CardTitle>ElevenLabs API Calls</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[600px] overflow-y-auto">
              {callsLoading && <p className="text-muted-foreground">Loading...</p>}
              {elevenLabsCalls?.items.length === 0 && (
                <p className="text-muted-foreground">No calls found in ElevenLabs</p>
              )}
              {elevenLabsCalls?.items.map((call) => (
                <div
                  key={call.conversation_id}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedElevenLabsId === call.conversation_id
                      ? 'bg-primary/10 border-primary'
                      : 'hover:bg-muted/50'
                  }`}
                  onClick={() => setSelectedElevenLabsId(call.conversation_id)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-mono text-xs">
                        {call.conversation_id.slice(0, 12)}...
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatUnixTime(call.start_time_unix)}
                      </div>
                    </div>
                    <Badge variant={call.call_successful === 'true' ? 'default' : 'outline'}>
                      {call.status}
                    </Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{formatDuration(call.call_duration_secs)}</span>
                    <span>{call.message_count} turns</span>
                    {call.direction && <span>{call.direction}</span>}
                  </div>
                  {call.transcript_summary && (
                    <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
                      {call.transcript_summary}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Call Detail */}
          <Card>
            <CardHeader>
              <CardTitle>Call Detail</CardTitle>
            </CardHeader>
            <CardContent className="max-h-[600px] overflow-y-auto">
              {!selectedElevenLabsId && (
                <p className="text-muted-foreground text-center py-8">
                  Select a call to view details
                </p>
              )}
              {callDetail && (
                <div className="space-y-4">
                  {/* Metadata */}
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Conversation ID:</span>
                      <span className="font-mono text-xs">{callDetail.conversation_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge>{callDetail.status}</Badge>
                    </div>
                    {callDetail.start_time_unix && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Started:</span>
                        <span>{formatUnixTime(callDetail.start_time_unix)}</span>
                      </div>
                    )}
                    {callDetail.call_duration_secs && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Duration:</span>
                        <span>{formatDuration(callDetail.call_duration_secs)}</span>
                      </div>
                    )}
                    {callDetail.cost !== null && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Cost:</span>
                        <span>${callDetail.cost.toFixed(4)}</span>
                      </div>
                    )}
                  </div>

                  {/* Summary */}
                  {callDetail.transcript_summary && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <div className="text-xs font-medium text-muted-foreground mb-1">Summary</div>
                      <p className="text-sm">{callDetail.transcript_summary}</p>
                    </div>
                  )}

                  {/* Transcript with tool calls */}
                  <div className="space-y-2">
                    <div className="text-sm font-medium">
                      Transcript ({callDetail.transcript.length} turns)
                    </div>
                    {callDetail.transcript.map((turn, idx) => (
                      <div key={idx} className="space-y-1">
                        <div
                          className={`p-2 rounded text-sm ${
                            turn.role === 'user' ? 'bg-blue-500/10 ml-4' : 'bg-primary/10 mr-4'
                          }`}
                        >
                          <div className="flex justify-between">
                            <span className="text-xs font-medium capitalize">{turn.role}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDuration(Math.round(turn.time_in_call_secs))}
                            </span>
                          </div>
                          <div className="mt-1">{turn.message}</div>
                        </div>

                        {/* Tool Calls */}
                        {turn.tool_calls && turn.tool_calls.length > 0 && (
                          <div className="ml-8 p-2 bg-yellow-500/10 rounded text-xs">
                            <span className="font-medium">Tool Call:</span>
                            <pre className="mt-1 overflow-x-auto">
                              {JSON.stringify(turn.tool_calls, null, 2)}
                            </pre>
                          </div>
                        )}

                        {/* Tool Results */}
                        {turn.tool_results && turn.tool_results.length > 0 && (
                          <div className="ml-8 p-2 bg-green-500/10 rounded text-xs">
                            <span className="font-medium">Tool Result:</span>
                            <pre className="mt-1 overflow-x-auto">
                              {JSON.stringify(turn.tool_results, null, 2)}
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
      )}

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-4">
        Data refreshes every 30 seconds
      </div>
    </div>
  )
}
