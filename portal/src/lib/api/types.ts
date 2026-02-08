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
  consecutive_in_zone: number
  consecutive_clingy_days: number
  consecutive_distant_days: number
  recent_transitions: Array<{
    from_state: string | null
    to_state: string
    reason: string | null
    created_at: string
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

export interface AdminUserDetail {
  id: string
  telegram_id: number | null
  phone: string | null
  relationship_score: number
  chapter: number
  boss_attempts: number
  days_played: number
  game_status: string
  last_interaction_at: string | null
  created_at: string
  updated_at: string
}

export interface AdminStats {
  total_users: number
  active_users: number
  new_users_7d: number
  total_conversations: number
  avg_relationship_score: number
}

export interface PipelineStageHealth {
  name: string
  is_critical: boolean
  avg_duration_ms: number
  success_rate: number
  runs_24h: number
  failures_24h: number
  timeout_seconds: number
}

export interface PipelineHealth {
  status: string
  pipeline_version: string
  stages: PipelineStageHealth[]
  total_runs_24h: number
  overall_success_rate: number
  avg_pipeline_duration_ms: number
  last_run_at: string | null
}

export interface StageFailure {
  stage_name: string
  conversation_id: string
  error_message: string
  occurred_at: string
}

export interface VoiceConversation {
  id: string
  user_id: string
  user_identifier: string | null
  platform: string
  started_at: string
  ended_at: string | null
  status: string
  score_delta: number | null
  emotional_tone: string | null
  message_count: number
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

export interface ProcessingStats {
  success_rate: number
  avg_duration_ms: number
  total_processed: number
  success_count: number
  failed_count: number
  pending_count: number
  stuck_count: number
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

export interface AdminConversationsResponse {
  conversations: AdminConversationItem[]
  total_count: number
  page: number
  page_size: number
  days: number
}

export interface AdminConversationItem {
  id: string
  user_id: string
  user_identifier: string | null
  platform: string
  started_at: string
  ended_at: string | null
  status: string
  score_delta: number | null
  emotional_tone: string | null
  message_count: number
}

export interface GeneratedPromptsResponse {
  prompts: PromptRecord[]
  total_count: number
  page: number
  page_size: number
}
