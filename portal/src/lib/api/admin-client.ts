import { createClient } from '../supabase/client'
import type {
  SystemOverviewResponse,
  JobStatusResponse,
  UserListResponse,
  UserListFilters,
  UserDetailResponse,
  StateMachinesResponse,
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
}

export const adminApiClient = new AdminApiClient()
