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

// ============================================================================
// Prompt Viewing Types (Spec 018)
// ============================================================================

export interface PromptListItem {
  id: string
  token_count: number
  generation_time_ms: number
  meta_prompt_template: string
  created_at: string
  conversation_id: string | null
}

export interface PromptListResponse {
  items: PromptListItem[]
  count: number
  user_id: string
}

export interface PromptDetailResponse {
  id: string | null
  prompt_content: string
  token_count: number
  generation_time_ms: number
  meta_prompt_template: string
  context_snapshot: Record<string, unknown> | null
  conversation_id: string | null
  created_at: string | null
  is_preview: boolean
  message: string | null
}

// ============================================================================
// Voice Monitoring Types (Phase 3.1)
// ============================================================================

export interface VoiceConversationListItem {
  id: string
  user_id: string
  user_name: string | null
  started_at: string
  ended_at: string | null
  message_count: number
  score_delta: number | null
  chapter_at_time: number | null
  elevenlabs_session_id: string | null
  status: 'active' | 'processing' | 'processed' | 'failed'
  conversation_summary: string | null
}

export interface VoiceConversationListResponse {
  items: VoiceConversationListItem[]
  count: number
  has_more: boolean
}

export interface TranscriptEntry {
  role: 'user' | 'nikita' | 'agent'
  content: string
  timestamp: string | null
}

export interface VoiceConversationDetailResponse {
  id: string
  user_id: string
  user_name: string | null
  started_at: string
  ended_at: string | null
  message_count: number
  score_delta: number | null
  chapter_at_time: number | null
  elevenlabs_session_id: string | null
  status: string
  conversation_summary: string | null
  emotional_tone: string | null
  transcript_raw: string | null
  messages: TranscriptEntry[]
  extracted_entities: Record<string, unknown> | null
  processed_at: string | null
}

export interface ElevenLabsCallListItem {
  conversation_id: string
  agent_id: string
  start_time_unix: number
  call_duration_secs: number
  message_count: number
  status: string
  call_successful: string | null
  transcript_summary: string | null
  direction: string | null
}

export interface ElevenLabsCallListResponse {
  items: ElevenLabsCallListItem[]
  has_more: boolean
  next_cursor: string | null
}

export interface ElevenLabsTranscriptTurn {
  role: 'user' | 'agent'
  message: string
  time_in_call_secs: number
  tool_calls: Record<string, unknown>[] | null
  tool_results: Record<string, unknown>[] | null
}

export interface ElevenLabsCallDetailResponse {
  conversation_id: string
  agent_id: string
  status: string
  transcript: ElevenLabsTranscriptTurn[]
  start_time_unix: number | null
  call_duration_secs: number | null
  cost: number | null
  transcript_summary: string | null
  call_successful: string | null
  has_audio: boolean
}

export interface VoiceStatsResponse {
  total_calls_24h: number
  total_calls_7d: number
  total_calls_30d: number
  avg_call_duration_secs: number | null
  calls_by_chapter: Record<number, number>
  calls_by_status: Record<string, number>
  processing_stats: Record<string, number>
}

// ============================================================================
// Text Monitoring Types (Phase 4.1)
// ============================================================================

export interface TextConversationListItem {
  id: string
  user_id: string
  user_name: string | null
  started_at: string
  ended_at: string | null
  message_count: number
  score_delta: number | null
  chapter_at_time: number | null
  is_boss_fight: boolean
  status: 'active' | 'processing' | 'processed' | 'failed'
  conversation_summary: string | null
  emotional_tone: string | null
}

export interface TextConversationListResponse {
  items: TextConversationListItem[]
  count: number
  has_more: boolean
}

export interface MessageEntry {
  role: 'user' | 'nikita'
  content: string
  timestamp: string | null
  analysis: Record<string, unknown> | null
}

export interface TextConversationDetailResponse {
  id: string
  user_id: string
  user_name: string | null
  started_at: string
  ended_at: string | null
  message_count: number
  score_delta: number | null
  chapter_at_time: number | null
  is_boss_fight: boolean
  status: string
  conversation_summary: string | null
  emotional_tone: string | null
  messages: MessageEntry[]
  extracted_entities: Record<string, unknown> | null
  processed_at: string | null
  processing_attempts: number
  last_message_at: string | null
}

export interface PipelineStageStatus {
  stage_name: string
  stage_number: number
  completed: boolean
  result_summary: string | null
}

export interface PipelineStatusResponse {
  conversation_id: string
  status: string
  processing_attempts: number
  processed_at: string | null
  stages: PipelineStageStatus[]
  threads_created: number
  thoughts_created: number
  entities_extracted: number
  summary: string | null
}

export interface TextStatsResponse {
  total_conversations_24h: number
  total_conversations_7d: number
  total_conversations_30d: number
  total_messages_24h: number
  avg_messages_per_conversation: number | null
  conversations_by_chapter: Record<number, number>
  conversations_by_status: Record<string, number>
  boss_fights_24h: number
  processing_stats: Record<string, number>
}

export interface ThreadListItem {
  id: string
  user_id: string
  thread_type: string
  topic: string | null
  is_active: boolean
  message_count: number
  created_at: string
  last_mentioned_at: string | null
}

export interface ThreadListResponse {
  items: ThreadListItem[]
  count: number
}

export interface ThoughtListItem {
  id: string
  user_id: string
  content: string
  thought_type: string | null
  created_at: string
}

export interface ThoughtListResponse {
  items: ThoughtListItem[]
  count: number
}
