/**
 * Mock data factories for E2E tests.
 * All types match TypeScript interfaces from portal/src/lib/api/types.ts.
 * Factories accept partial overrides for flexible test scenarios.
 */

import type {
  UserStats, UserMetrics, EngagementData, DecayStatus,
  VicePreference, Conversation, ConversationDetail, ConversationMessage,
  DailySummary, UserSettings, AdminUser, AdminStats, AdminUserDetail,
  PipelineHealth, PipelineStageHealth, JobStatus, PipelineRun,
  PipelineEvent, ScoreHistory, ScorePoint,
  EmotionalStateResponse, LifeEventsResponse, LifeEventItem,
  SocialCircleResponse, SocialCircleMember,
  PsycheTipsData, NarrativeArcsResponse, NarrativeArcItem,
  ThoughtsResponse, ThoughtItem,
  AdminConversationsResponse, AdminConversationItem,
  GeneratedPromptsResponse, PromptRecord,
  VoiceConversation,
  DetailedScoreHistory, DetailedScorePoint,
} from "../../src/lib/api/types"

// ─── Player factories ───

export function mockMetrics(overrides: Partial<UserMetrics> = {}): UserMetrics {
  return {
    intimacy: 0.65,
    passion: 0.55,
    trust: 0.7,
    secureness: 0.6,
    weights: { intimacy: 0.25, passion: 0.25, trust: 0.25, secureness: 0.25 },
    ...overrides,
  }
}

export function mockUser(overrides: Partial<UserStats> = {}): UserStats {
  return {
    id: "e2e-player-id",
    relationship_score: 62,
    chapter: 2,
    chapter_name: "Infatuation",
    boss_threshold: 65,
    progress_to_boss: 45,
    days_played: 12,
    game_status: "active",
    last_interaction_at: new Date().toISOString(),
    boss_attempts: 0,
    metrics: mockMetrics(),
    ...overrides,
  }
}

export function mockScoreHistory(overrides: Partial<ScoreHistory> = {}): ScoreHistory {
  const points: ScorePoint[] = Array.from({ length: 10 }, (_, i) => ({
    score: 50 + i * 2,
    chapter: i < 5 ? 1 : 2,
    event_type: i % 3 === 0 ? "conversation" : null,
    recorded_at: new Date(Date.now() - (10 - i) * 86400000).toISOString(),
  }))
  return { points, total_count: 10, ...overrides }
}

export function mockDetailedScoreHistory(overrides: Partial<DetailedScoreHistory> = {}): DetailedScoreHistory {
  const points: DetailedScorePoint[] = Array.from({ length: 5 }, (_, i) => ({
    id: `sp-${i}`,
    score: 55 + i * 3,
    chapter: 2,
    event_type: "conversation",
    recorded_at: new Date(Date.now() - (5 - i) * 86400000).toISOString(),
    intimacy_delta: 0.02,
    passion_delta: 0.01,
    trust_delta: 0.03,
    secureness_delta: -0.01,
    score_delta: 1.5,
    conversation_id: `conv-${i}`,
  }))
  return { points, total_count: 5, ...overrides }
}

export function mockEngagement(overrides: Partial<EngagementData> = {}): EngagementData {
  return {
    state: "in_zone",
    multiplier: 1.2,
    calibration_score: 75,
    consecutive_in_zone: 3,
    consecutive_clingy_days: 0,
    consecutive_distant_days: 0,
    recent_transitions: [
      { from_state: "calibrating", to_state: "in_zone", reason: "Consistent contact", created_at: new Date().toISOString() },
    ],
    ...overrides,
  }
}

export function mockDecay(overrides: Partial<DecayStatus> = {}): DecayStatus {
  return {
    grace_period_hours: 24,
    hours_remaining: 18,
    decay_rate: 0.5,
    current_score: 62,
    projected_score: 59,
    is_decaying: false,
    ...overrides,
  }
}

export function mockConversations(overrides: { conversations?: Partial<Conversation>[]; total?: number } = {}): { conversations: Conversation[]; total: number } {
  const conversations: Conversation[] = (overrides.conversations ?? [
    { id: "conv-1", user_id: "e2e-player-id", platform: "telegram", started_at: new Date().toISOString(), ended_at: null, message_count: 8, score_delta: 2.5, emotional_tone: "playful", is_boss_fight: false },
    { id: "conv-2", user_id: "e2e-player-id", platform: "telegram", started_at: new Date(Date.now() - 86400000).toISOString(), ended_at: new Date(Date.now() - 82800000).toISOString(), message_count: 14, score_delta: -1.0, emotional_tone: "tense", is_boss_fight: false },
  ]).map((c) => ({
    id: "conv-default",
    user_id: "e2e-player-id",
    platform: "telegram",
    started_at: new Date().toISOString(),
    ended_at: null,
    message_count: 5,
    score_delta: null,
    emotional_tone: null,
    is_boss_fight: false,
    ...c,
  }))
  return { conversations, total: overrides.total ?? conversations.length }
}

export function mockConversationDetail(overrides: Partial<ConversationDetail> = {}): ConversationDetail {
  const messages: ConversationMessage[] = [
    { id: "msg-1", role: "user", content: "Hey Nikita, how are you?", created_at: new Date().toISOString() },
    { id: "msg-2", role: "assistant", content: "I'm doing great! I was just thinking about you.", created_at: new Date().toISOString() },
    { id: "msg-3", role: "user", content: "That's sweet!", created_at: new Date().toISOString() },
  ]
  return {
    id: "conv-detail-1",
    platform: "telegram",
    started_at: new Date().toISOString(),
    ended_at: null,
    messages,
    score_delta: 2.5,
    emotional_tone: "playful",
    extracted_entities: ["dinner", "weekend plans"],
    conversation_summary: "Casual conversation with playful tone about weekend plans.",
    is_boss_fight: false,
    ...overrides,
  }
}

export function mockVices(overrides?: Partial<VicePreference>[]): VicePreference[] {
  const defaults: VicePreference[] = [
    { category: "jealousy", intensity_level: 3, engagement_score: 0.72, discovered_at: new Date().toISOString() },
    { category: "possessiveness", intensity_level: 2, engagement_score: 0.55, discovered_at: new Date().toISOString() },
  ]
  if (overrides) {
    return overrides.map((o, i) => ({ ...defaults[i % defaults.length], ...o }))
  }
  return defaults
}

export function mockDiary(overrides?: Partial<DailySummary>[]): DailySummary[] {
  const defaults: DailySummary[] = [
    { id: "diary-1", date: new Date().toISOString().slice(0, 10), score_start: 60, score_end: 63, decay_applied: 0.5, conversations_count: 2, summary_text: "A warm day full of playful exchanges.", emotional_tone: "warm" },
    { id: "diary-2", date: new Date(Date.now() - 86400000).toISOString().slice(0, 10), score_start: 58, score_end: 60, decay_applied: 1.0, conversations_count: 1, summary_text: "Brief but meaningful connection.", emotional_tone: "tender" },
  ]
  if (overrides) {
    return overrides.map((o, i) => ({ ...defaults[i % defaults.length], ...o }))
  }
  return defaults
}

export function mockSettings(overrides: Partial<UserSettings> = {}): UserSettings {
  return {
    email: "e2e-player@test.local",
    timezone: "America/New_York",
    telegram_linked: true,
    telegram_username: "e2e_player",
    notifications_enabled: true,
    ...overrides,
  }
}

export function mockInsights(overrides: Partial<DetailedScoreHistory> = {}): DetailedScoreHistory {
  return mockDetailedScoreHistory(overrides)
}

export function mockNikitaMind(): EmotionalStateResponse {
  return {
    state_id: "es-1",
    arousal: 0.6,
    valence: 0.7,
    dominance: 0.5,
    intimacy: 0.65,
    conflict_state: "none",
    conflict_started_at: null,
    conflict_trigger: null,
    description: "Feeling warm and content, thinking about you.",
    last_updated: new Date().toISOString(),
  }
}

export function mockNikitaCircle(): SocialCircleResponse {
  const friends: SocialCircleMember[] = [
    { id: "friend-1", friend_name: "Anya", friend_role: "best friend", age: 26, occupation: "barista", personality: "bubbly and supportive", relationship_to_nikita: "Childhood best friend", storyline_potential: ["coffee date", "relationship advice"], is_active: true },
    { id: "friend-2", friend_name: "Marcus", friend_role: "colleague", age: 30, occupation: "designer", personality: "quiet and observant", relationship_to_nikita: "Work partner", storyline_potential: ["project deadline", "office drama"], is_active: true },
  ]
  return { friends, total_count: 2 }
}

export function mockNikitaDay(): PsycheTipsData {
  return {
    attachment_style: "anxious-preoccupied",
    defense_mode: "people-pleasing",
    emotional_tone: "warm but cautious",
    vulnerability_level: 0.6,
    behavioral_tips: [
      "She responds well to reassurance",
      "Avoid dismissive responses",
      "Ask about her day — she loves sharing details",
    ],
    topics_to_encourage: ["weekend plans", "creative hobbies", "future together"],
    topics_to_avoid: ["ex-relationships", "long silences"],
    internal_monologue: "I hope they reach out today. Maybe I should text first... no, I'll wait.",
    generated_at: new Date().toISOString(),
  }
}

export function mockNikitaStories(): NarrativeArcsResponse {
  const active: NarrativeArcItem[] = [
    {
      id: "arc-1", template_name: "Weekend Getaway", category: "romance", current_stage: "rising",
      stage_progress: 0.4, conversations_in_arc: 3, max_conversations: 8,
      current_description: "Nikita hinted at wanting to go somewhere special this weekend.",
      involved_characters: ["Nikita", "Player"], emotional_impact: { intimacy: 0.1, passion: 0.15 },
      is_active: true, started_at: new Date(Date.now() - 3 * 86400000).toISOString(), resolved_at: null,
    },
  ]
  const resolved: NarrativeArcItem[] = [
    {
      id: "arc-0", template_name: "First Fight", category: "conflict", current_stage: "resolved",
      stage_progress: 1.0, conversations_in_arc: 5, max_conversations: 5,
      current_description: "You resolved your first real disagreement together.",
      involved_characters: ["Nikita", "Player"], emotional_impact: { trust: 0.2, secureness: 0.1 },
      is_active: false, started_at: new Date(Date.now() - 10 * 86400000).toISOString(), resolved_at: new Date(Date.now() - 7 * 86400000).toISOString(),
    },
  ]
  return { active_arcs: active, resolved_arcs: resolved, total_count: 2 }
}

// ─── Admin factories ───

export function mockAdminStats(overrides: Partial<AdminStats> = {}): AdminStats {
  return {
    total_users: 47,
    active_users: 23,
    new_users_7d: 5,
    total_conversations: 312,
    avg_relationship_score: 58.4,
    ...overrides,
  }
}

export function mockAdminUsers(overrides?: Partial<AdminUser>[]): AdminUser[] {
  const defaults: AdminUser[] = [
    { id: "user-1", telegram_id: "12345", email: "alice@example.com", relationship_score: 72, chapter: 3, engagement_state: "in_zone", game_status: "active", last_interaction_at: new Date().toISOString(), created_at: new Date(Date.now() - 30 * 86400000).toISOString() },
    { id: "user-2", telegram_id: null, email: "bob@example.com", relationship_score: 45, chapter: 1, engagement_state: "distant", game_status: "active", last_interaction_at: new Date(Date.now() - 7 * 86400000).toISOString(), created_at: new Date(Date.now() - 14 * 86400000).toISOString() },
  ]
  if (overrides) {
    return overrides.map((o, i) => ({ ...defaults[i % defaults.length], ...o }))
  }
  return defaults
}

export function mockAdminUserDetail(overrides: Partial<AdminUserDetail> = {}): AdminUserDetail {
  return {
    id: "user-1",
    telegram_id: 12345,
    phone: "+1234567890",
    relationship_score: 72,
    chapter: 3,
    boss_attempts: 1,
    days_played: 30,
    game_status: "active",
    last_interaction_at: new Date().toISOString(),
    created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

export function mockPipelineHealth(overrides: Partial<PipelineHealth> = {}): PipelineHealth {
  const stages: PipelineStageHealth[] = [
    { name: "context_build", is_critical: true, avg_duration_ms: 120, success_rate: 98.5, runs_24h: 50, failures_24h: 1, timeout_seconds: 30 },
    { name: "score_calc", is_critical: true, avg_duration_ms: 45, success_rate: 100, runs_24h: 50, failures_24h: 0, timeout_seconds: 15 },
    { name: "memory_write", is_critical: false, avg_duration_ms: 200, success_rate: 96, runs_24h: 50, failures_24h: 2, timeout_seconds: 60 },
  ]
  return {
    status: "healthy",
    pipeline_version: "2.1.0",
    stages,
    total_runs_24h: 50,
    overall_success_rate: 97.5,
    avg_pipeline_duration_ms: 850,
    last_run_at: new Date().toISOString(),
    ...overrides,
  }
}

export function mockPipelineEvents(overrides?: Partial<PipelineEvent>[]): PipelineEvent[] {
  const defaults: PipelineEvent[] = [
    { id: "pe-1", user_id: "user-1", conversation_id: "conv-1", event_type: "pipeline_run", stage: "context_build", data: { status: "success" }, duration_ms: 120, created_at: new Date().toISOString() },
    { id: "pe-2", user_id: "user-1", conversation_id: "conv-1", event_type: "pipeline_run", stage: "score_calc", data: { status: "success" }, duration_ms: 45, created_at: new Date().toISOString() },
  ]
  if (overrides) {
    return overrides.map((o, i) => ({ ...defaults[i % defaults.length], ...o }))
  }
  return defaults
}

export function mockJobs(overrides?: Partial<JobStatus>[]): JobStatus[] {
  const defaults: JobStatus[] = [
    { name: "decay-processor", last_run: new Date().toISOString(), status: "success", executions_24h: 24, failures_24h: 0 },
    { name: "daily-summary", last_run: new Date().toISOString(), status: "success", executions_24h: 1, failures_24h: 0 },
    { name: "engagement-eval", last_run: new Date(Date.now() - 3600000).toISOString(), status: "failed", executions_24h: 24, failures_24h: 2 },
  ]
  if (overrides) {
    return overrides.map((o, i) => ({ ...defaults[i % defaults.length], ...o }))
  }
  return defaults
}

export function mockPipelineRuns(count = 3): PipelineRun[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `run-${i}`,
    started_at: new Date(Date.now() - i * 3600000).toISOString(),
    completed_at: new Date(Date.now() - i * 3600000 + 850).toISOString(),
    success: i !== 2,
    stages: [
      { name: "context_build", duration_ms: 120, status: "success" as const },
      { name: "score_calc", duration_ms: 45, status: "success" as const },
      { name: "memory_write", duration_ms: 200, status: i === 2 ? "failed" as const : "success" as const },
    ],
  }))
}

export function mockAdminConversations(overrides: Partial<AdminConversationsResponse> = {}): AdminConversationsResponse {
  const conversations: AdminConversationItem[] = [
    { id: "conv-a1", user_id: "user-1", user_identifier: "alice@example.com", platform: "telegram", started_at: new Date().toISOString(), ended_at: null, status: "active", score_delta: 2.5, emotional_tone: "playful", message_count: 8 },
    { id: "conv-a2", user_id: "user-2", user_identifier: "bob@example.com", platform: "telegram", started_at: new Date(Date.now() - 86400000).toISOString(), ended_at: new Date(Date.now() - 82800000).toISOString(), status: "completed", score_delta: -1.0, emotional_tone: "tense", message_count: 14 },
  ]
  return {
    conversations,
    total_count: 2,
    page: 1,
    page_size: 20,
    days: 7,
    ...overrides,
  }
}

export function mockGeneratedPrompts(overrides: Partial<GeneratedPromptsResponse> = {}): GeneratedPromptsResponse {
  const prompts: PromptRecord[] = [
    { id: "prompt-1", user_id: "user-1", platform: "telegram", token_count: 1250, created_at: new Date().toISOString() },
    { id: "prompt-2", user_id: "user-2", platform: "voice", token_count: 980, created_at: new Date(Date.now() - 3600000).toISOString() },
  ]
  return { prompts, total_count: 2, page: 1, page_size: 20, ...overrides }
}

export function mockVoiceConversations(count = 2): VoiceConversation[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `voice-${i}`,
    user_id: `user-${i + 1}`,
    user_identifier: `user${i + 1}@example.com`,
    platform: "voice",
    started_at: new Date(Date.now() - i * 3600000).toISOString(),
    ended_at: i === 0 ? null : new Date(Date.now() - i * 3600000 + 600000).toISOString(),
    status: i === 0 ? "active" : "completed",
    score_delta: i === 0 ? null : 1.5,
    emotional_tone: "warm",
    message_count: 12 + i * 3,
  }))
}

// ─── Onboarding factories ───

export function mockOnboardingProfile() {
  return {
    location_city: "Zurich",
    social_scene: "techno" as const,
    drug_tolerance: 3,
    life_stage: "tech" as const,
    interest: "AI and music",
  }
}

export function mockNewUserStats() {
  return {
    ...mockUser(),
    onboarded_at: null,
  }
}

export function mockOnboardedUserStats() {
  return {
    ...mockUser(),
    onboarded_at: "2026-03-22T14:00:00Z",
  }
}

export function mockThoughts(): ThoughtsResponse {
  const thoughts: ThoughtItem[] = [
    { id: "t-1", thought_type: "curiosity", content: "I wonder what they did today...", source_conversation_id: "conv-1", expires_at: null, used_at: null, is_expired: false, psychological_context: null, created_at: new Date().toISOString() },
  ]
  return { thoughts, total_count: 1, has_more: false }
}

export function mockLifeEvents(): LifeEventsResponse {
  const events: LifeEventItem[] = [
    { event_id: "le-1", time_of_day: "morning", domain: "work", event_type: "meeting", description: "Had a team stand-up at the office", entities: ["office", "team"], importance: 0.3, emotional_impact: null, narrative_arc_id: null },
    { event_id: "le-2", time_of_day: "afternoon", domain: "social", event_type: "coffee", description: "Met Anya for coffee", entities: ["Anya", "coffee shop"], importance: 0.6, emotional_impact: { arousal_delta: 0.1, valence_delta: 0.15, dominance_delta: 0, intimacy_delta: 0.05 }, narrative_arc_id: null },
  ]
  return { events, date: new Date().toISOString().slice(0, 10), total_count: 2 }
}
