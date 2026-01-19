import { createClient } from '../supabase/client'
import type {
  SystemOverviewResponse,
  JobStatusResponse,
  UserListResponse,
  UserListFilters,
  UserDetailResponse,
  StateMachinesResponse,
  // Voice monitoring types
  VoiceConversationListResponse,
  VoiceConversationDetailResponse,
  VoiceStatsResponse,
  ElevenLabsCallListResponse,
  ElevenLabsCallDetailResponse,
  // Text monitoring types
  TextConversationListResponse,
  TextConversationDetailResponse,
  TextStatsResponse,
  PipelineStatusResponse,
  ThreadListResponse,
  ThoughtListResponse,
  // Prompt viewing types
  PromptListResponse,
  PromptDetailResponse,
} from './admin-types'

const API_URL = process.env.NEXT_PUBLIC_API_URL

class AdminApiClient {
  private async getAuthHeaders(): Promise<HeadersInit> {
    const supabase = createClient()
    const {
      data: { session },
    } = await supabase.auth.getSession()

    if (!session) {
      throw new Error('Not authenticated')
    }

    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
    }
  }

  /**
   * Check if user is admin based on email domain or explicit allowlist.
   * Uses backend as authoritative source - tries to access admin endpoint.
   */
  async isAdmin(): Promise<boolean> {
    const supabase = createClient()
    const {
      data: { user },
    } = await supabase.auth.getUser()

    if (!user?.email) {
      return false
    }

    // Quick check: @silent-agents.com domain is always admin
    if (user.email.endsWith('@silent-agents.com')) {
      return true
    }

    // For other emails, verify against backend (authoritative source)
    // This handles the explicit admin allowlist configured via ADMIN_EMAILS env var
    try {
      const headers = await this.getAuthHeaders()
      const response = await fetch(`${API_URL}/admin/debug/system`, {
        method: 'GET',
        headers,
      })
      return response.status === 200
    } catch {
      return false
    }
  }

  /**
   * Get system overview stats
   * AC-FR002-001: Returns user counts by game_status
   * AC-FR002-002: Returns user distribution by chapter
   * AC-FR002-003: Returns user distribution by engagement_state
   * AC-FR010-001: Returns active user counts (24h, 7d, 30d)
   */
  async getSystemOverview(): Promise<SystemOverviewResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/system`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Admin access required')
      }
      throw new Error(`Failed to fetch system overview: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get scheduled jobs status
   * AC-FR008-001: Returns all 5 job types listed
   * AC-FR008-002: Returns last_run timestamp
   * AC-FR008-003: Returns status (running, completed, failed)
   * AC-FR008-004: Returns duration_ms of last run
   * AC-FR008-005: Returns error info for failed jobs
   */
  async getJobStatus(): Promise<JobStatusResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/jobs`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Admin access required')
      }
      throw new Error(`Failed to fetch job status: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get paginated user list for admin debug
   * AC-FR003-001: Returns paginated list (50 per page default)
   * AC-FR003-002: Supports filter by game_status query param
   * AC-FR003-003: Supports filter by chapter query param
   */
  async getUsers(filters: UserListFilters = {}): Promise<UserListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()

    if (filters.page) params.set('page', filters.page.toString())
    if (filters.page_size) params.set('page_size', filters.page_size.toString())
    if (filters.game_status) params.set('game_status', filters.game_status)
    if (filters.chapter) params.set('chapter', filters.chapter.toString())

    const url = `${API_URL}/admin/debug/users${params.toString() ? `?${params.toString()}` : ''}`
    const response = await fetch(url, { headers })

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Admin access required')
      }
      throw new Error(`Failed to fetch users: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get user detail for debugging
   */
  async getUserDetail(userId: string): Promise<UserDetailResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/users/${userId}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Admin access required')
      }
      if (response.status === 404) {
        throw new Error('User not found')
      }
      throw new Error(`Failed to fetch user detail: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get all state machine status for a user
   */
  async getStateMachines(userId: string): Promise<StateMachinesResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/state-machines/${userId}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Admin access required')
      }
      if (response.status === 404) {
        throw new Error('User not found')
      }
      throw new Error(`Failed to fetch state machines: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // Voice Monitoring Methods (Phase 3)
  // ============================================================================

  /**
   * Get voice conversations from database
   */
  async getVoiceConversations(
    limit = 50,
    offset = 0,
    userId?: string
  ): Promise<VoiceConversationListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    if (userId) params.set('user_id', userId)

    const response = await fetch(
      `${API_URL}/admin/debug/voice/conversations?${params.toString()}`,
      { headers }
    )

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch voice conversations: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get voice conversation detail with transcript
   */
  async getVoiceConversationDetail(
    conversationId: string
  ): Promise<VoiceConversationDetailResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/voice/conversations/${conversationId}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      if (response.status === 404) throw new Error('Conversation not found')
      throw new Error(`Failed to fetch voice conversation: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get voice call statistics
   */
  async getVoiceStats(): Promise<VoiceStatsResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/voice/stats`, { headers })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch voice stats: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get calls from ElevenLabs API
   */
  async getElevenLabsCalls(limit = 30): Promise<ElevenLabsCallListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()
    params.set('limit', limit.toString())

    const response = await fetch(`${API_URL}/admin/debug/voice/elevenlabs?${params.toString()}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch ElevenLabs calls: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get call detail from ElevenLabs with transcript
   */
  async getElevenLabsCallDetail(conversationId: string): Promise<ElevenLabsCallDetailResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/voice/elevenlabs/${conversationId}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      if (response.status === 404) throw new Error('Call not found')
      throw new Error(`Failed to fetch ElevenLabs call: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // Text Monitoring Methods (Phase 4)
  // ============================================================================

  /**
   * Get text conversations from database
   */
  async getTextConversations(
    limit = 50,
    offset = 0,
    userId?: string
  ): Promise<TextConversationListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    if (userId) params.set('user_id', userId)

    const response = await fetch(`${API_URL}/admin/debug/text/conversations?${params.toString()}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch text conversations: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get text conversation detail with messages
   */
  async getTextConversationDetail(conversationId: string): Promise<TextConversationDetailResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/text/conversations/${conversationId}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      if (response.status === 404) throw new Error('Conversation not found')
      throw new Error(`Failed to fetch text conversation: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get text conversation statistics
   */
  async getTextStats(): Promise<TextStatsResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/text/stats`, { headers })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch text stats: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get post-processing pipeline status for a conversation
   */
  async getPipelineStatus(conversationId: string): Promise<PipelineStatusResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/text/pipeline/${conversationId}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      if (response.status === 404) throw new Error('Conversation not found')
      throw new Error(`Failed to fetch pipeline status: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get conversation threads for a user
   */
  async getThreads(userId: string, limit = 50): Promise<ThreadListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()
    params.set('limit', limit.toString())

    const response = await fetch(
      `${API_URL}/admin/debug/text/threads/${userId}?${params.toString()}`,
      { headers }
    )

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch threads: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get Nikita thoughts for a user
   */
  async getThoughts(userId: string, limit = 50): Promise<ThoughtListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()
    params.set('limit', limit.toString())

    const response = await fetch(
      `${API_URL}/admin/debug/text/thoughts/${userId}?${params.toString()}`,
      { headers }
    )

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch thoughts: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // Prompt Viewing Methods (Spec 018)
  // ============================================================================

  /**
   * Get prompts for a user
   */
  async getUserPrompts(userId: string, limit = 20): Promise<PromptListResponse> {
    const headers = await this.getAuthHeaders()
    const params = new URLSearchParams()
    params.set('limit', limit.toString())

    const response = await fetch(`${API_URL}/admin/debug/prompts/${userId}?${params.toString()}`, {
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch prompts: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get prompt detail with full content
   */
  async getPromptDetail(promptId: string): Promise<PromptDetailResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/prompts/detail/${promptId}`, { headers })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      if (response.status === 404) throw new Error('Prompt not found')
      throw new Error(`Failed to fetch prompt: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get latest prompt for a user
   */
  async getLatestPrompt(userId: string): Promise<PromptDetailResponse> {
    const headers = await this.getAuthHeaders()
    const response = await fetch(`${API_URL}/admin/debug/prompts/${userId}/latest`, { headers })

    if (!response.ok) {
      if (response.status === 403) throw new Error('Admin access required')
      throw new Error(`Failed to fetch latest prompt: ${response.statusText}`)
    }

    return response.json()
  }
}

export const adminApiClient = new AdminApiClient()
