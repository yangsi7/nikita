'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/supabase/client'
import { useConversations } from '@/hooks/use-dashboard-data'
import { ConversationList } from '@/components/history/ConversationList'
import { ConversationDetail } from '@/components/history/ConversationDetail'
import { Card, CardContent } from '@/components/ui/card'
import { Navigation } from '@/components/layout/Navigation'

export default function ConversationsPage() {
  const router = useRouter()
  const { data: conversations = [], isLoading } = useConversations(50) // Show last 50
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const selectedConversation = conversations.find((c) => c.id === selectedId)

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
      <main className="container mx-auto px-4 py-8">
        {/* Page Title */}
        <div className="mb-6">
          <h2 className="text-3xl font-bold mb-2">Conversation History</h2>
          <p className="text-muted-foreground">Review your past interactions with Nikita</p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <Card className="border-border/50 bg-card/50">
            <CardContent className="py-12">
              <div className="text-center space-y-3">
                <div className="text-4xl animate-pulse">💬</div>
                <p className="text-sm text-muted-foreground">Loading conversations...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Content Grid */}
        {!isLoading && (
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Conversation List */}
            <div>
              <ConversationList
                conversations={conversations}
                onSelectConversation={setSelectedId}
              />
            </div>

            {/* Conversation Detail */}
            <div className="lg:sticky lg:top-24 lg:h-fit">
              {selectedConversation ? (
                <ConversationDetail conversation={selectedConversation} />
              ) : (
                <Card className="border-border/50 bg-card/50">
                  <CardContent className="py-12">
                    <div className="text-center space-y-3">
                      <div className="text-4xl">👈</div>
                      <p className="text-sm text-muted-foreground">
                        Select a conversation to view details
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
