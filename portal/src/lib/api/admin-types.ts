// Admin Debug Portal API response types
// Matches backend schemas in nikita/api/schemas/admin_debug.py

// ============================================================================
// System Overview Types (T2.1)
// ============================================================================

export interface GameStatusDistribution {
  active: number
  boss_fight: number
  game_over: number
  won: number
}

export interface ChapterDistribution {
  chapter_1: number
  chapter_2: number
  chapter_3: number
  chapter_4: number
  chapter_5: number
}

export interface EngagementDistribution {
  calibrating: number
  in_zone: number
  drifting: number
  clingy: number
  distant: number
  out_of_zone: number
}

export interface ActiveUserCounts {
  last_24h: number
  last_7d: number
  last_30d: number
}

export interface SystemOverviewResponse {
  total_users: number
  game_status: GameStatusDistribution
  chapters: ChapterDistribution
  engagement_states: EngagementDistribution
  active_users: ActiveUserCounts
}

// ============================================================================
// Job Monitoring Types (T2.2)
// ============================================================================

export interface JobExecutionStatus {
  job_name: string
  last_run_at: string | null
  last_status: 'running' | 'completed' | 'failed' | null
  last_duration_ms: number | null
  last_result: Record<string, unknown> | null
  runs_24h: number
  failures_24h: number
}

export interface JobStatusResponse {
  jobs: JobExecutionStatus[]
  recent_failures: JobExecutionStatus[]
}

// ============================================================================
// User List Types (T2.3)
// ============================================================================

export interface UserListItem {
  id: string
  telegram_id: number | null
  email: string | null
  relationship_score: number
  chapter: number
  engagement_state: string | null
  game_status: string
  last_interaction_at: string | null
  created_at: string
}

export interface UserListResponse {
  users: UserListItem[]
  total_count: number
  page: number
  page_size: number
}

export interface UserListFilters {
  page?: number
  page_size?: number
  game_status?: string
  chapter?: number
}

// ============================================================================
// User Detail Types (T2.4)
// ============================================================================

export interface UserTimingInfo {
  grace_period_remaining_hours: number
  is_in_grace_period: boolean
  decay_rate_per_hour: number
  hours_since_last_interaction: number
  next_decay_at: string | null
  boss_ready: boolean
  boss_attempts_remaining: number
}

export interface UserNextActions {
  should_decay: boolean
  decay_due_at: string | null
  can_trigger_boss: boolean
  boss_threshold: number
  score_to_boss: number
}

export interface UserDetailResponse {
  id: string
  telegram_id: number | null
  email: string | null
  phone: string | null
  relationship_score: number
  chapter: number
  chapter_name: string
  boss_attempts: number
  days_played: number
  game_status: string
  timing: UserTimingInfo
  next_actions: UserNextActions
  created_at: string
  updated_at: string
  last_interaction_at: string | null
}

// ============================================================================
// State Machine Types (T2.5)
// ============================================================================

export interface EngagementStateInfo {
  current_state: string
  multiplier: number
  calibration_score: number
  consecutive_in_zone: number
  consecutive_clingy_days: number
  consecutive_distant_days: number
  recent_transitions: {
    from_state: string
    to_state: string
    reason: string
    created_at: string | null
  }[]
}

export interface ChapterStateInfo {
  current_chapter: number
  chapter_name: string
  boss_threshold: number
  current_score: number
  progress_to_boss: number
  boss_attempts: number
  can_trigger_boss: boolean
}

export interface ViceInfo {
  category: string
  intensity_level: number
  engagement_score: number
  discovered_at: string
}

export interface ViceProfileInfo {
  top_vices: ViceInfo[]
  total_vices_discovered: number
  expression_level: string | null
}

export interface StateMachinesResponse {
  user_id: string
  engagement: EngagementStateInfo
  chapter: ChapterStateInfo
  vice_profile: ViceProfileInfo
}
