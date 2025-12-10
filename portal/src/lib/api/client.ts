import { createClient } from '../supabase/client'
import type {
  UserStats,
  EngagementState,
  Vice,
  Conversation,
  DailySummary,
  ScoreHistoryPoint,
} from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL

class ApiClient {
  private async getAuthHeaders(): Promise<HeadersInit> {
    const supabase = createClient()
    const {
      data: { session },
    } = await supabase.auth.getSession()

    if (!session) {
      console.error('[API] No active session found')
      throw new Error('Not authenticated')
    }

    console.log('[API] Session valid, user ID:', session.user?.id)
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
    }
  }

  async getUserStats(): Promise<UserStats> {
    const headers = await this.getAuthHeaders()
    console.log('[API] Fetching user stats from:', `${API_URL}/api/v1/portal/stats`)
    console.log('[API] API_URL value:', API_URL)

    const response = await fetch(`${API_URL}/api/v1/portal/stats`, {
      headers,
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[API] Stats fetch failed:', {
        status: response.status,
        statusText: response.statusText,
        error: errorText,
        url: `${API_URL}/api/v1/portal/stats`,
      })
      throw new Error(`Failed to fetch user stats: ${response.statusText}`)
    }

    const data = await response.json()
    console.log('[API] User stats received successfully')
    return data
  }

  async getEngagement(): Promise<EngagementState> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/api/v1/portal/engagement`, {
      headers,
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch engagement: ${response.statusText}`)
    }

    return response.json()
  }

  async getVices(): Promise<Vice[]> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/api/v1/portal/vices`, {
      headers,
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch vices: ${response.statusText}`)
    }

    return response.json()
  }

  async getConversations(limit = 10): Promise<Conversation[]> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/api/v1/portal/conversations?limit=${limit}`, {
      headers,
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch conversations: ${response.statusText}`)
    }

    return response.json()
  }

  async getDailySummary(date: string): Promise<DailySummary> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/api/v1/portal/daily-summary/${date}`, {
      headers,
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch daily summary: ${response.statusText}`)
    }

    return response.json()
  }

  async getScoreHistory(days = 30): Promise<ScoreHistoryPoint[]> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/api/v1/portal/score-history?days=${days}`, {
      headers,
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch score history: ${response.statusText}`)
    }

    return response.json()
  }
}

export const apiClient = new ApiClient()
