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
  score_delta: number | null
  emotional_tone: string | null
  extracted_entities: string[] | null
  conversation_summary: string | null
  is_boss_fight: boolean
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

// Spec 046 — Emotional Intelligence

export interface EmotionalStateResponse {
  state_id: string
  arousal: number
  valence: number
  dominance: number
  intimacy: number
  conflict_state: "none" | "passive_aggressive" | "cold" | "vulnerable" | "explosive"
  conflict_started_at: string | null
  conflict_trigger: string | null
  description: string
  last_updated: string
}

export interface EmotionalStatePoint {
  arousal: number
  valence: number
  dominance: number
  intimacy: number
  conflict_state: string
  recorded_at: string
}

export interface EmotionalStateHistory {
  points: EmotionalStatePoint[]
  total_count: number
}

export interface EmotionalImpact {
  arousal_delta: number
  valence_delta: number
  dominance_delta: number
  intimacy_delta: number
}

export interface LifeEventItem {
  event_id: string
  time_of_day: "morning" | "afternoon" | "evening" | "night"
  domain: "work" | "social" | "personal"
  event_type: string
  description: string
  entities: string[]
  importance: number
  emotional_impact: EmotionalImpact | null
  narrative_arc_id: string | null
}

export interface LifeEventsResponse {
  events: LifeEventItem[]
  date: string
  total_count: number
}

export interface ThoughtItem {
  id: string
  thought_type: string
  content: string
  source_conversation_id: string | null
  expires_at: string | null
  used_at: string | null
  is_expired: boolean
  psychological_context: Record<string, unknown> | null
  created_at: string
}

export interface ThoughtsResponse {
  thoughts: ThoughtItem[]
  total_count: number
  has_more: boolean
}

export interface NarrativeArcItem {
  id: string
  template_name: string
  category: string
  current_stage: "setup" | "rising" | "climax" | "falling" | "resolved"
  stage_progress: number
  conversations_in_arc: number
  max_conversations: number
  current_description: string | null
  involved_characters: string[]
  emotional_impact: Record<string, number>
  is_active: boolean
  started_at: string
  resolved_at: string | null
}

export interface NarrativeArcsResponse {
  active_arcs: NarrativeArcItem[]
  resolved_arcs: NarrativeArcItem[]
  total_count: number
}

export interface SocialCircleMember {
  id: string
  friend_name: string
  friend_role: string
  age: number | null
  occupation: string | null
  personality: string | null
  relationship_to_nikita: string | null
  storyline_potential: string[]
  is_active: boolean
}

export interface SocialCircleResponse {
  friends: SocialCircleMember[]
  total_count: number
}

// Spec 047 — Deep Insights

export interface DetailedScorePoint {
  id: string
  score: number
  chapter: number
  event_type: string | null
  recorded_at: string
  intimacy_delta: number | null
  passion_delta: number | null
  trust_delta: number | null
  secureness_delta: number | null
  score_delta: number | null
  conversation_id: string | null
}

export interface DetailedScoreHistory {
  points: DetailedScorePoint[]
  total_count: number
}

export interface Thread {
  id: string
  thread_type: string
  content: string
  status: string
  source_conversation_id: string | null
  created_at: string
  resolved_at: string | null
}

export interface ThreadList {
  threads: Thread[]
  total_count: number
  open_count: number
}
