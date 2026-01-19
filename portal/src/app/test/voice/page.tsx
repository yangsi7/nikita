'use client'

import { useState, useCallback } from 'react'
import { useConversation } from '@elevenlabs/react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// Test user created in Supabase with game_status='active', chapter=2
const TEST_USER_ID = '2fec9cdf-871d-4840-828f-95b40d437985'
// Use local API proxy to avoid CORS and hide backend URL

interface AvailabilityResponse {
  available: boolean
  reason: string
  chapter: number
  availability_rate: number
}

interface Message {
  role: 'user' | 'agent'
  text: string
  timestamp: Date
}

export default function VoiceTestPage() {
  const [availability, setAvailability] = useState<AvailabilityResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])

  const conversation = useConversation({
    onConnect: () => {
      console.log('[VOICE] Connected to ElevenLabs')
      setError(null)
    },
    onDisconnect: () => {
      console.log('[VOICE] Disconnected')
    },
    onMessage: (msg) => {
      console.log('[VOICE] Message:', msg)
      if (msg.message) {
        setMessages((prev) => [
          ...prev,
          {
            role: msg.source === 'user' ? 'user' : 'agent',
            text: msg.message,
            timestamp: new Date(),
          },
        ])
      }
    },
    onError: (err) => {
      console.error('[VOICE] Error:', err)
      setError(typeof err === 'string' ? err : (err as Error)?.message || 'Voice error occurred')
    },
  })

  const checkAvailability = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/voice/availability/${TEST_USER_ID}`)
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setAvailability(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to check availability')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const startCall = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setMessages([])

    try {
      // Request microphone permission first
      console.log('[VOICE] Requesting microphone permission...')
      await navigator.mediaDevices.getUserMedia({ audio: true })
      console.log('[VOICE] Microphone permission granted')

      // Get signed URL from backend
      console.log('[VOICE] Fetching signed URL...')
      const res = await fetch(`/api/voice/signed-url/${TEST_USER_ID}`)
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || `HTTP ${res.status}`)
      }
      const { signed_url, agent_id } = await res.json()
      console.log('[VOICE] Got signed URL, agent:', agent_id)

      // Start ElevenLabs conversation
      console.log('[VOICE] Starting session...')
      await conversation.startSession({
        signedUrl: signed_url,
        connectionType: 'websocket',
      })
      console.log('[VOICE] Session started!')
    } catch (e) {
      console.error('[VOICE] Start call error:', e)
      setError(e instanceof Error ? e.message : 'Failed to start call')
    } finally {
      setIsLoading(false)
    }
  }, [conversation])

  const endCall = useCallback(async () => {
    console.log('[VOICE] Ending session...')
    await conversation.endSession()
    console.log('[VOICE] Session ended')
  }, [conversation])

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-2xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Voice Agent Test</h1>
          <p className="text-muted-foreground">Test ElevenLabs Conversational AI integration</p>
        </div>

        {/* Connection Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Connection Status
              <Badge
                variant={
                  conversation.status === 'connected'
                    ? 'default'
                    : conversation.status === 'connecting'
                      ? 'secondary'
                      : 'outline'
                }
              >
                {conversation.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Speaking:</span>
              <Badge variant={conversation.isSpeaking ? 'default' : 'outline'}>
                {conversation.isSpeaking ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">Test User ID:</span>
              <code className="ml-2 rounded bg-muted p-1 text-xs">{TEST_USER_ID}</code>
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">API:</span>
              <code className="ml-2 rounded bg-muted p-1 text-xs">/api/voice/* (proxy)</code>
            </div>
          </CardContent>
        </Card>

        {/* Availability Check */}
        <Card>
          <CardHeader>
            <CardTitle>Availability Check</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={checkAvailability} disabled={isLoading}>
              {isLoading ? 'Checking...' : 'Check Availability'}
            </Button>
            {availability && (
              <div className="space-y-2 rounded-lg bg-muted p-4">
                <div className="flex items-center gap-2">
                  <span>Available:</span>
                  <Badge variant={availability.available ? 'default' : 'destructive'}>
                    {availability.available ? 'Yes' : 'No'}
                  </Badge>
                </div>
                <div className="text-sm">
                  <strong>Chapter:</strong> {availability.chapter}
                </div>
                <div className="text-sm">
                  <strong>Rate:</strong> {(availability.availability_rate * 100).toFixed(0)}%
                </div>
                <div className="text-sm">
                  <strong>Reason:</strong> {availability.reason}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Call Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Voice Call</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <Button
                onClick={startCall}
                disabled={isLoading || conversation.status === 'connected'}
                className="flex-1"
              >
                {isLoading ? 'Starting...' : 'Start Call'}
              </Button>
              <Button
                onClick={endCall}
                variant="destructive"
                disabled={conversation.status !== 'connected'}
                className="flex-1"
              >
                End Call
              </Button>
            </div>

            {error && (
              <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
                <p className="text-destructive">{error}</p>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              Note: Browser will ask for microphone permission when starting a call.
            </p>
          </CardContent>
        </Card>

        {/* Conversation Transcript */}
        <Card>
          <CardHeader>
            <CardTitle>Conversation Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 space-y-2 overflow-y-auto">
              {messages.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No messages yet. Start a call to see the transcript.
                </p>
              ) : (
                messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`rounded-lg p-3 ${
                      msg.role === 'user' ? 'ml-8 bg-primary/10' : 'mr-8 bg-muted'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">
                        {msg.role === 'user' ? 'You' : 'Nikita'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {msg.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="mt-1">{msg.text}</p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Debug Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Debug Console</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Open browser DevTools (F12) to see detailed logs with [VOICE] prefix.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
