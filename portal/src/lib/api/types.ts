export interface UserMetrics {
  intimacy: number
  passion: number
  trust: number
  secureness: number
  weights: {
    intimacy: number
    passion: number
    trust: number
    secureness: number
  }
}

export interface UserStats {
  id: string
  relationship_score: number
  chapter: number
  chapter_name: string
  boss_threshold: number
  progress_to_boss: number
  days_played: number
  game_status: "active" | "boss_fight" | "game_over" | "won"
  last_interaction_at: string | null
  boss_attempts: number
  metrics: UserMetrics
}

export interface ScorePoint {
  score: number
  chapter: number
  event_type: string | null
  recorded_at: string
}

export interface ScoreHistory {
  points: ScorePoint[]
  total_count: number
}

export interface EngagementData {
  state: string
  multiplier: number
  calibration_score: number | null
  consecutive_short: number
  consecutive_long: number
  recent_transitions: Array<{
    from_state: string
    to_state: string
    timestamp: string
    reason: string
  }>
}

export interface DecayStatus {
  grace_period_hours: number
  hours_remaining: number
  decay_rate: number
  current_score: number
  projected_score: number
  is_decaying: boolean
}

export interface VicePreference {
  category: string
  intensity_level: number
  engagement_score: number
  discovered_at: string
}

export interface Conversation {
  id: string
  user_id: string
  platform: string
  started_at: string
  ended_at: string | null
  message_count: number
  score_delta: number | null
  tone: string | null
}

export interface ConversationMessage {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
}

export interface ConversationDetail {
  id: string
  platform: string
  started_at: string
  ended_at: string | null
  messages: ConversationMessage[]
}

export interface DailySummary {
  id: string
  date: string
  summary_text: string
  tone: string
  score_start: number
  score_end: number
  conversation_count: number
}

export interface UserSettings {
  email: string
  timezone: string | null
  telegram_linked: boolean
  telegram_username: string | null
  notifications_enabled: boolean
}

// Admin types
export interface AdminUser {
  id: string
  telegram_id: string | null
  email: string | null
  relationship_score: number
  chapter: number
  engagement_state: string
  game_status: string
  last_interaction_at: string | null
  created_at: string
}

export interface AdminUserDetail extends AdminUser {
  metrics: UserMetrics
  vices: VicePreference[]
  boss_attempts: number
  days_played: number
}

export interface AdminStats {
  active_users_24h: number
  new_signups_7d: number
  pipeline_success_rate: number
  avg_processing_time_ms: number
  error_rate_24h: number
  active_voice_calls: number
}

export interface PipelineStageHealth {
  name: string
  success_rate: number
  avg_duration_ms: number
  error_count: number
}

export interface PipelineHealth {
  stages: PipelineStageHealth[]
  recent_failures: Array<{
    conversation_id: string
    stage: string
    error: string
    timestamp: string
  }>
}

export interface VoiceConversation {
  id: string
  user_id: string
  agent_id: string
  started_at: string
  ended_at: string | null
  duration_seconds: number
  status: string
}

export interface PromptRecord {
  id: string
  user_id: string
  platform: string
  token_count: number
  created_at: string
}

export interface PromptDetail extends PromptRecord {
  prompt_content: string
  meta_prompt_template: string
  context_snapshot: Record<string, unknown> | null
}

export interface JobStatus {
  name: string
  last_run: string | null
  status: "success" | "failed" | "running" | "unknown"
  executions_24h: number
  failures_24h: number
}

export interface PipelineRun {
  id: string
  started_at: string
  completed_at: string | null
  success: boolean
  stages: Array<{
    name: string
    duration_ms: number
    status: "success" | "failed" | "skipped"
  }>
}

export interface ApiError {
  detail: string
  status: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
