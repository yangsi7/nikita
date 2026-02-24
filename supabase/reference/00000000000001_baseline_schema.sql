-- Comprehensive Baseline Schema for Nikita Database
-- Generated: 2026-02-24 from production Supabase instance
-- Captures all 64 applied migrations as a single reproducible baseline.
--
-- NOTE: This file is a documentation artifact for schema reproducibility.
-- Do NOT apply via `supabase db push` on an existing database — it will
-- conflict with already-applied migrations. Use only for new environments.
--
-- Contains: extensions, enums, tables, functions, indexes, RLS policies, triggers.
-- Subsequent migration stubs (20251129*–20260223*) are no-ops; all DDL is here.
--
-- Prerequisites:
--   - Supabase project with pgVector extension enabled
--   - Extensions: vector, pg_cron, pg_net

-- ============================================================================
-- EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- ============================================================================
-- ENUMS
-- ============================================================================
DO $$ BEGIN
    CREATE TYPE engagement_state_enum AS ENUM (
        'calibrating', 'in_zone', 'drifting', 'clingy', 'distant', 'out_of_zone'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- TABLES
-- ============================================================================

-- users
CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY,
    telegram_id bigint UNIQUE,
    phone varchar,
    relationship_score numeric NOT NULL DEFAULT 50.00,
    chapter integer NOT NULL DEFAULT 1,
    boss_attempts integer NOT NULL DEFAULT 0,
    days_played integer NOT NULL DEFAULT 0,
    last_interaction_at timestamptz,
    game_status varchar NOT NULL DEFAULT 'active',
    timezone varchar NOT NULL DEFAULT 'UTC',
    notifications_enabled boolean NOT NULL DEFAULT true,
    cached_voice_prompt text,
    cached_voice_prompt_at timestamptz,
    cached_voice_context jsonb,
    onboarding_status text DEFAULT 'pending',
    onboarding_profile jsonb DEFAULT '{}'::jsonb,
    onboarded_at timestamptz,
    onboarding_call_id text,
    boss_fight_started_at timestamptz,
    routine_config jsonb DEFAULT '{}'::jsonb,
    meta_instructions jsonb DEFAULT '{}'::jsonb,
    last_conflict_at timestamptz,
    conflict_details jsonb,
    cool_down_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- user_metrics
CREATE TABLE IF NOT EXISTS user_metrics (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intimacy numeric NOT NULL DEFAULT 50.00,
    passion numeric NOT NULL DEFAULT 50.00,
    trust numeric NOT NULL DEFAULT 50.00,
    secureness numeric NOT NULL DEFAULT 50.00,
    vulnerability_exchanges integer DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- user_vice_preferences
CREATE TABLE IF NOT EXISTS user_vice_preferences (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category varchar NOT NULL,
    intensity_level integer NOT NULL DEFAULT 1,
    engagement_score numeric NOT NULL DEFAULT 0.00,
    discovered_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- conversations
CREATE TABLE IF NOT EXISTS conversations (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform varchar NOT NULL,
    messages jsonb NOT NULL DEFAULT '[]'::jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    score_delta numeric,
    is_boss_fight boolean NOT NULL DEFAULT false,
    chapter_at_time integer NOT NULL DEFAULT 1,
    search_vector tsvector,
    status text DEFAULT 'active',
    processing_attempts integer DEFAULT 0,
    processed_at timestamptz,
    last_message_at timestamptz,
    extracted_entities jsonb,
    conversation_summary text,
    emotional_tone text,
    elevenlabs_session_id text,
    transcript_raw text,
    processing_started_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- score_history
CREATE TABLE IF NOT EXISTS score_history (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score numeric NOT NULL,
    chapter integer NOT NULL,
    event_type varchar,
    event_details jsonb,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- daily_summaries
CREATE TABLE IF NOT EXISTS daily_summaries (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date date NOT NULL,
    score_start numeric,
    score_end numeric,
    decay_applied numeric,
    conversations_count integer NOT NULL DEFAULT 0,
    nikita_summary_text text,
    key_events jsonb,
    summary_text text,
    key_moments jsonb,
    emotional_tone text,
    engagement_score numeric,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- engagement_state
CREATE TABLE IF NOT EXISTS engagement_state (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    state engagement_state_enum NOT NULL DEFAULT 'calibrating',
    calibration_score numeric NOT NULL DEFAULT 0.5,
    consecutive_in_zone integer NOT NULL DEFAULT 0,
    consecutive_clingy_days integer NOT NULL DEFAULT 0,
    consecutive_distant_days integer NOT NULL DEFAULT 0,
    multiplier numeric NOT NULL DEFAULT 0.9,
    last_calculated_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- engagement_history
CREATE TABLE IF NOT EXISTS engagement_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_state engagement_state_enum,
    to_state engagement_state_enum NOT NULL,
    reason text,
    calibration_score numeric,
    clinginess_score numeric,
    neglect_score numeric,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- conversation_threads
CREATE TABLE IF NOT EXISTS conversation_threads (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_type text NOT NULL,
    content text NOT NULL,
    source_conversation_id uuid REFERENCES conversations(id),
    status text DEFAULT 'open',
    created_at timestamptz DEFAULT now(),
    resolved_at timestamptz
);

-- nikita_thoughts
CREATE TABLE IF NOT EXISTS nikita_thoughts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thought_type text NOT NULL,
    content text NOT NULL,
    source_conversation_id uuid REFERENCES conversations(id),
    expires_at timestamptz,
    used_at timestamptz,
    psychological_context jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

-- message_embeddings
CREATE TABLE IF NOT EXISTS message_embeddings (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_index integer NOT NULL,
    embedding extensions.vector,
    content_preview text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- generated_prompts
CREATE TABLE IF NOT EXISTS generated_prompts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES conversations(id),
    prompt_content text NOT NULL,
    token_count integer NOT NULL,
    generation_time_ms double precision NOT NULL,
    meta_prompt_template varchar NOT NULL,
    context_snapshot jsonb,
    platform varchar DEFAULT 'text',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- job_executions
CREATE TABLE IF NOT EXISTS job_executions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name varchar NOT NULL,
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    status varchar NOT NULL DEFAULT 'running',
    result jsonb,
    duration_ms integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- pending_registrations
CREATE TABLE IF NOT EXISTS pending_registrations (
    telegram_id bigint PRIMARY KEY,
    email varchar NOT NULL,
    chat_id bigint,
    otp_state varchar NOT NULL DEFAULT 'pending',
    otp_attempts integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '10 minutes')
);

-- scheduled_events
CREATE TABLE IF NOT EXISTS scheduled_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform varchar NOT NULL,
    event_type varchar NOT NULL,
    content jsonb NOT NULL,
    scheduled_at timestamptz NOT NULL,
    delivered_at timestamptz,
    status varchar NOT NULL DEFAULT 'pending',
    retry_count integer NOT NULL DEFAULT 0,
    error_message text,
    source_conversation_id uuid REFERENCES conversations(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- scheduled_touchpoints
CREATE TABLE IF NOT EXISTS scheduled_touchpoints (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_type varchar NOT NULL,
    trigger_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    message_content text NOT NULL DEFAULT '',
    delivery_at timestamptz NOT NULL,
    delivered boolean NOT NULL DEFAULT false,
    delivered_at timestamptz,
    skipped boolean NOT NULL DEFAULT false,
    skip_reason varchar,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id uuid NOT NULL,
    admin_email text NOT NULL,
    action text NOT NULL,
    resource_type text NOT NULL,
    resource_id uuid,
    user_id uuid,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

-- error_logs
CREATE TABLE IF NOT EXISTS error_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    level varchar NOT NULL DEFAULT 'error',
    message text NOT NULL,
    source varchar NOT NULL,
    user_id uuid,
    conversation_id uuid,
    stack_trace text,
    context jsonb NOT NULL DEFAULT '{}'::jsonb,
    resolved boolean NOT NULL DEFAULT false,
    resolution_notes text,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- user_profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    location_city varchar,
    location_country varchar,
    life_stage varchar,
    social_scene varchar,
    primary_interest varchar,
    drug_tolerance integer NOT NULL DEFAULT 3,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- user_backstories
CREATE TABLE IF NOT EXISTS user_backstories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    venue_name varchar,
    venue_city varchar,
    scenario_type varchar,
    how_we_met text,
    the_moment text,
    unresolved_hook text,
    nikita_persona_overrides jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- onboarding_states
CREATE TABLE IF NOT EXISTS onboarding_states (
    telegram_id bigint PRIMARY KEY,
    current_step varchar NOT NULL DEFAULT 'location',
    collected_answers jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- venue_cache
CREATE TABLE IF NOT EXISTS venue_cache (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    city varchar NOT NULL,
    scene varchar NOT NULL,
    venues jsonb NOT NULL DEFAULT '[]'::jsonb,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days')
);

-- context_packages
CREATE TABLE IF NOT EXISTS context_packages (
    id bigserial PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    package jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '24 hours')
);

-- nikita_emotional_states
CREATE TABLE IF NOT EXISTS nikita_emotional_states (
    state_id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    arousal numeric NOT NULL DEFAULT 0.5,
    valence numeric NOT NULL DEFAULT 0.5,
    dominance numeric NOT NULL DEFAULT 0.5,
    intimacy numeric NOT NULL DEFAULT 0.5,
    conflict_state text NOT NULL DEFAULT 'none',
    conflict_started_at timestamptz,
    conflict_trigger text,
    ignored_message_count integer NOT NULL DEFAULT 0,
    conflict_details jsonb DEFAULT '{}'::jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    last_updated timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- nikita_entities
CREATE TABLE IF NOT EXISTS nikita_entities (
    entity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type varchar NOT NULL,
    name varchar NOT NULL,
    description text,
    relationship text,
    created_at timestamptz DEFAULT now()
);

-- nikita_life_events
CREATE TABLE IF NOT EXISTS nikita_life_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_date date NOT NULL,
    time_of_day varchar NOT NULL,
    domain varchar NOT NULL,
    event_type varchar NOT NULL,
    description text NOT NULL,
    entities jsonb DEFAULT '[]'::jsonb,
    emotional_impact jsonb NOT NULL DEFAULT '{"arousal_delta":0,"valence_delta":0,"dominance_delta":0,"intimacy_delta":0}'::jsonb,
    importance double precision NOT NULL DEFAULT 0.5,
    narrative_arc_id uuid,
    created_at timestamptz DEFAULT now()
);

-- nikita_narrative_arcs
CREATE TABLE IF NOT EXISTS nikita_narrative_arcs (
    arc_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain varchar NOT NULL,
    arc_type varchar NOT NULL,
    status varchar DEFAULT 'active',
    start_date date NOT NULL,
    entities jsonb DEFAULT '[]'::jsonb,
    current_state text,
    possible_outcomes jsonb DEFAULT '[]'::jsonb,
    created_at timestamptz DEFAULT now(),
    resolved_at timestamptz
);

-- user_social_circles
CREATE TABLE IF NOT EXISTS user_social_circles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_name text NOT NULL,
    friend_role text NOT NULL,
    age integer,
    occupation text,
    personality text,
    relationship_to_nikita text,
    storyline_potential jsonb DEFAULT '[]'::jsonb,
    trigger_conditions jsonb DEFAULT '[]'::jsonb,
    adapted_traits jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    last_event timestamptz,
    sentiment text DEFAULT 'neutral',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- user_narrative_arcs
CREATE TABLE IF NOT EXISTS user_narrative_arcs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_name text NOT NULL,
    category text NOT NULL,
    current_stage text NOT NULL DEFAULT 'setup',
    stage_progress integer DEFAULT 0,
    conversations_in_arc integer DEFAULT 0,
    max_conversations integer DEFAULT 5,
    current_description text,
    involved_characters jsonb DEFAULT '[]'::jsonb,
    emotional_impact jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    started_at timestamptz DEFAULT now(),
    resolved_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- psyche_states
CREATE TABLE IF NOT EXISTS psyche_states (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state jsonb NOT NULL DEFAULT '{}'::jsonb,
    generated_at timestamptz DEFAULT now(),
    model text NOT NULL DEFAULT 'sonnet',
    token_count integer NOT NULL DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- push_subscriptions
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint text NOT NULL,
    p256dh text NOT NULL,
    auth text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- voice_calls
CREATE TABLE IF NOT EXISTS voice_calls (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    elevenlabs_session_id text,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    duration_seconds integer,
    transcript text,
    summary text,
    score_delta numeric,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- memory_facts
CREATE TABLE IF NOT EXISTS memory_facts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    graph_type text NOT NULL,
    fact text NOT NULL,
    source text NOT NULL,
    confidence real NOT NULL,
    embedding extensions.vector NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    is_active boolean NOT NULL DEFAULT true,
    superseded_by uuid,
    conversation_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- ready_prompts
CREATE TABLE IF NOT EXISTS ready_prompts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform text NOT NULL,
    prompt_text text NOT NULL,
    token_count integer NOT NULL,
    context_snapshot jsonb,
    pipeline_version text NOT NULL,
    generation_time_ms real NOT NULL,
    is_current boolean NOT NULL DEFAULT true,
    conversation_id uuid,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- is_admin: Used by RLS policies to grant admin access
CREATE OR REPLACE FUNCTION public.is_admin()
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
    RETURN (
        SELECT email LIKE '%@silent-agents.com'
        FROM auth.users
        WHERE id = auth.uid()
    );
END;
$function$;

-- calculate_hours_since_interaction: Used by decay engine
CREATE OR REPLACE FUNCTION public.calculate_hours_since_interaction(p_user_id uuid)
 RETURNS double precision
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
    SELECT EXTRACT(EPOCH FROM (NOW() - COALESCE(last_interaction_at, created_at))) / 3600.0
    FROM users
    WHERE id = p_user_id;
$function$;

-- cleanup_expired_registrations: Called by pg_cron
CREATE OR REPLACE FUNCTION public.cleanup_expired_registrations()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
BEGIN
    DELETE FROM pending_registrations
    WHERE expires_at < now();
END;
$function$;

-- trigger_set_updated_at: Generic updated_at trigger function
CREATE OR REPLACE FUNCTION public.trigger_set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$function$;

-- update_updated_at_column: Generic updated_at trigger function (alternate)
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

-- NOTE: 7 legacy functions exist in production but reference dropped tables
-- (nikita_state, user_facts) or stale column names. They are excluded from
-- this baseline to avoid errors on fresh deployments:
--   create_user_with_state, get_recent_conversations, get_user_context_summary,
--   match_user_facts, search_user_facts, update_fact_reference, update_user_scores

-- ============================================================================
-- INDEXES (non-primary-key)
-- ============================================================================

-- audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_admin ON audit_logs USING btree (admin_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs USING btree (user_id, created_at DESC);

-- context_packages
CREATE INDEX IF NOT EXISTS idx_context_packages_expires ON context_packages USING btree (user_id, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_context_packages_gin ON context_packages USING gin (package);
CREATE UNIQUE INDEX IF NOT EXISTS idx_context_packages_user_id ON context_packages USING btree (user_id);

-- conversation_threads
CREATE INDEX IF NOT EXISTS idx_conversation_threads_source_conversation_id ON conversation_threads USING btree (source_conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_user_status ON conversation_threads USING btree (user_id, status) WHERE (status = 'open'::text);

-- conversations
CREATE INDEX IF NOT EXISTS idx_conversations_platform ON conversations USING btree (platform);
CREATE INDEX IF NOT EXISTS idx_conversations_session_detection ON conversations USING btree (user_id, status, last_message_at) WHERE (status = 'active'::text);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON conversations USING btree (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations USING btree (status);
CREATE INDEX IF NOT EXISTS idx_conversations_stuck_detection ON conversations USING btree (status, processing_started_at) WHERE (status = 'processing'::text);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations USING btree (user_id, status);
CREATE INDEX IF NOT EXISTS ix_conversations_search_vector ON conversations USING gin (search_vector);
CREATE INDEX IF NOT EXISTS ix_conversations_started_at ON conversations USING btree (started_at DESC);
CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations USING btree (user_id);

-- daily_summaries
CREATE UNIQUE INDEX IF NOT EXISTS daily_summaries_user_id_date_key ON daily_summaries USING btree (user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_user_date ON daily_summaries USING btree (user_id, date DESC);

-- engagement_history
CREATE INDEX IF NOT EXISTS idx_engagement_history_created_at ON engagement_history USING btree (created_at);
CREATE INDEX IF NOT EXISTS idx_engagement_history_user_id ON engagement_history USING btree (user_id);

-- engagement_state
CREATE INDEX IF NOT EXISTS idx_engagement_state_user_id ON engagement_state USING btree (user_id);

-- error_logs
CREATE INDEX IF NOT EXISTS idx_error_logs_level ON error_logs USING btree (level);
CREATE INDEX IF NOT EXISTS idx_error_logs_occurred_at ON error_logs USING btree (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_resolved ON error_logs USING btree (resolved);
CREATE INDEX IF NOT EXISTS idx_error_logs_source ON error_logs USING btree (source);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs USING btree (user_id);

-- generated_prompts
CREATE INDEX IF NOT EXISTS idx_generated_prompts_conversation_id ON generated_prompts USING btree (conversation_id);
CREATE INDEX IF NOT EXISTS idx_generated_prompts_created ON generated_prompts USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_prompts_created_at ON generated_prompts USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_prompts_template ON generated_prompts USING btree (meta_prompt_template);
CREATE INDEX IF NOT EXISTS idx_generated_prompts_user ON generated_prompts USING btree (user_id);
CREATE INDEX IF NOT EXISTS idx_generated_prompts_user_id ON generated_prompts USING btree (user_id);

-- job_executions
CREATE INDEX IF NOT EXISTS idx_job_executions_job_name_started ON job_executions USING btree (job_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_executions_status ON job_executions USING btree (status);

-- memory_facts
CREATE INDEX IF NOT EXISTS idx_memory_facts_embedding_cosine ON memory_facts USING ivfflat (embedding vector_cosine_ops) WITH (lists='50');
CREATE INDEX IF NOT EXISTS idx_memory_facts_user_graph_active ON memory_facts USING btree (user_id, graph_type, created_at DESC) WHERE (is_active = true);

-- message_embeddings
CREATE INDEX IF NOT EXISTS ix_message_embeddings_conversation_id ON message_embeddings USING btree (conversation_id);
CREATE INDEX IF NOT EXISTS ix_message_embeddings_user_id ON message_embeddings USING btree (user_id);
CREATE INDEX IF NOT EXISTS ix_message_embeddings_vector ON message_embeddings USING ivfflat (embedding vector_cosine_ops);

-- nikita_emotional_states
CREATE INDEX IF NOT EXISTS idx_emotional_states_conflict ON nikita_emotional_states USING btree (user_id, conflict_state) WHERE (conflict_state <> 'none'::text);
CREATE INDEX IF NOT EXISTS idx_emotional_states_conflict_details ON nikita_emotional_states USING gin (conflict_details);
CREATE INDEX IF NOT EXISTS idx_emotional_states_last_updated ON nikita_emotional_states USING btree (user_id, last_updated DESC);
CREATE INDEX IF NOT EXISTS idx_emotional_states_user_id ON nikita_emotional_states USING btree (user_id);

-- nikita_entities
CREATE INDEX IF NOT EXISTS idx_entities_user_type ON nikita_entities USING btree (user_id, entity_type);

-- nikita_life_events
CREATE INDEX IF NOT EXISTS idx_life_events_domain ON nikita_life_events USING btree (user_id, domain);
CREATE INDEX IF NOT EXISTS idx_life_events_user_date ON nikita_life_events USING btree (user_id, event_date);

-- nikita_narrative_arcs
CREATE INDEX IF NOT EXISTS idx_narrative_arcs_user_status ON nikita_narrative_arcs USING btree (user_id, status);

-- nikita_thoughts
CREATE INDEX IF NOT EXISTS idx_nikita_thoughts_source_conversation_id ON nikita_thoughts USING btree (source_conversation_id);
CREATE INDEX IF NOT EXISTS idx_nikita_thoughts_user_active ON nikita_thoughts USING btree (user_id, used_at, expires_at, created_at);

-- onboarding_states
CREATE INDEX IF NOT EXISTS idx_onboarding_states_step ON onboarding_states USING btree (current_step);

-- pending_registrations
CREATE INDEX IF NOT EXISTS ix_pending_registrations_expires_at ON pending_registrations USING btree (expires_at);

-- psyche_states
CREATE INDEX IF NOT EXISTS idx_psyche_states_user_id ON psyche_states USING btree (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS psyche_states_user_id_key ON psyche_states USING btree (user_id);

-- push_subscriptions
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user_id ON push_subscriptions USING btree (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS push_subscriptions_user_id_endpoint_key ON push_subscriptions USING btree (user_id, endpoint);

-- ready_prompts
CREATE UNIQUE INDEX IF NOT EXISTS idx_ready_prompts_current ON ready_prompts USING btree (user_id, platform) WHERE (is_current = true);
CREATE INDEX IF NOT EXISTS idx_ready_prompts_user_created ON ready_prompts USING btree (user_id, created_at DESC);

-- scheduled_events
CREATE INDEX IF NOT EXISTS idx_scheduled_events_due ON scheduled_events USING btree (status, scheduled_at) WHERE ((status)::text = 'pending'::text);
CREATE INDEX IF NOT EXISTS idx_scheduled_events_scheduled_at ON scheduled_events USING btree (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_events_status ON scheduled_events USING btree (status);
CREATE INDEX IF NOT EXISTS idx_scheduled_events_user_id ON scheduled_events USING btree (user_id);

-- scheduled_touchpoints
CREATE INDEX IF NOT EXISTS idx_scheduled_touchpoints_due ON scheduled_touchpoints USING btree (delivered, skipped, delivery_at) WHERE ((delivered = false) AND (skipped = false));
CREATE INDEX IF NOT EXISTS idx_scheduled_touchpoints_user_id ON scheduled_touchpoints USING btree (user_id);

-- score_history
CREATE INDEX IF NOT EXISTS idx_score_history_user_recorded ON score_history USING btree (user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_score_history_user_time ON score_history USING btree (user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_score_history_recorded_at ON score_history USING btree (recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_score_history_user_id ON score_history USING btree (user_id);

-- user_backstories
CREATE INDEX IF NOT EXISTS idx_user_backstories_user_id ON user_backstories USING btree (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS user_backstories_user_id_key ON user_backstories USING btree (user_id);

-- user_metrics
CREATE INDEX IF NOT EXISTS idx_user_metrics_user_id ON user_metrics USING btree (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS user_metrics_user_id_key ON user_metrics USING btree (user_id);

-- user_narrative_arcs
CREATE INDEX IF NOT EXISTS idx_narrative_arcs_active ON user_narrative_arcs USING btree (user_id, is_active) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_narrative_arcs_user_id ON user_narrative_arcs USING btree (user_id);

-- user_profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_drug_tolerance ON user_profiles USING btree (drug_tolerance);

-- user_social_circles
CREATE INDEX IF NOT EXISTS idx_social_circles_active ON user_social_circles USING btree (user_id, is_active) WHERE (is_active = true);
CREATE INDEX IF NOT EXISTS idx_social_circles_user_id ON user_social_circles USING btree (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_friend_name ON user_social_circles USING btree (user_id, friend_name);

-- user_vice_preferences
CREATE INDEX IF NOT EXISTS ix_user_vice_preferences_user_id ON user_vice_preferences USING btree (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS user_vice_preferences_user_id_category_key ON user_vice_preferences USING btree (user_id, category);

-- users
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users USING btree (telegram_id) WHERE (telegram_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS ix_users_game_status ON users USING btree (game_status);
CREATE INDEX IF NOT EXISTS ix_users_telegram_id ON users USING btree (telegram_id);

-- venue_cache
CREATE INDEX IF NOT EXISTS idx_venue_cache_city_scene ON venue_cache USING btree (city, scene);
CREATE INDEX IF NOT EXISTS idx_venue_cache_expires ON venue_cache USING btree (expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_venue_cache_city_scene ON venue_cache USING btree (city, scene);

-- voice_calls
CREATE INDEX IF NOT EXISTS idx_voice_calls_user_id ON voice_calls USING btree (user_id);

-- ============================================================================
-- ROW LEVEL SECURITY — Enable
-- ============================================================================
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE nikita_emotional_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE nikita_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE nikita_life_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE nikita_narrative_arcs ENABLE ROW LEVEL SECURITY;
ALTER TABLE nikita_thoughts ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE psyche_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ready_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_touchpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_backstories ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_narrative_arcs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_social_circles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_vice_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE venue_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_calls ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- ROW LEVEL SECURITY — Policies
-- ============================================================================

-- audit_logs
CREATE POLICY "audit_logs_service_role_only" ON audit_logs FOR ALL TO public USING (auth.role() = 'service_role'::text);

-- context_packages
CREATE POLICY "Users access own context packages" ON context_packages FOR ALL TO public USING (auth.uid() = user_id);

-- conversation_threads
CREATE POLICY "Service role full access threads" ON conversation_threads FOR ALL TO public USING ((SELECT auth.role() AS role) = 'service_role'::text);
CREATE POLICY "Users can view own threads" ON conversation_threads FOR SELECT TO public USING ((SELECT auth.uid() AS uid) = user_id);

-- conversations
CREATE POLICY "Admin reads all conversations" ON conversations FOR SELECT TO public USING (((SELECT (auth.uid() = conversations_1.user_id) FROM conversations conversations_1 WHERE (conversations_1.id = conversations_1.id)) OR is_admin()));
CREATE POLICY "Service role full access conversations" ON conversations FOR ALL TO service_role USING (true);
CREATE POLICY "Users can read own conversations" ON conversations FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "conversations_own_data" ON conversations FOR ALL TO public USING (user_id = (SELECT auth.uid() AS uid)) WITH CHECK (user_id = (SELECT auth.uid() AS uid));

-- daily_summaries
CREATE POLICY "Admin reads all daily_summaries" ON daily_summaries FOR SELECT TO public USING (((SELECT (auth.uid() = daily_summaries_1.user_id) FROM daily_summaries daily_summaries_1 WHERE (daily_summaries_1.id = daily_summaries_1.id)) OR is_admin()));
CREATE POLICY "Service role full access daily_summaries" ON daily_summaries FOR ALL TO service_role USING (true);
CREATE POLICY "daily_summaries_own_data" ON daily_summaries FOR ALL TO public USING (user_id = (SELECT auth.uid() AS uid)) WITH CHECK (user_id = (SELECT auth.uid() AS uid));

-- engagement_history
CREATE POLICY "Admin reads all engagement_history" ON engagement_history FOR SELECT TO public USING (((SELECT (auth.uid() = engagement_history_1.user_id) FROM engagement_history engagement_history_1 WHERE (engagement_history_1.id = engagement_history_1.id)) OR is_admin()));
CREATE POLICY "Service role can manage engagement history" ON engagement_history FOR ALL TO public USING ((SELECT auth.role() AS role) = 'service_role'::text);
CREATE POLICY "Users can view own engagement history" ON engagement_history FOR SELECT TO public USING (user_id = (SELECT auth.uid() AS uid));

-- engagement_state
CREATE POLICY "Admin reads all engagement_state" ON engagement_state FOR SELECT TO public USING (((SELECT auth.uid() AS uid) = user_id) OR is_admin());
CREATE POLICY "Admin updates engagement_state" ON engagement_state FOR UPDATE TO public USING (is_admin());
CREATE POLICY "Service role can manage engagement state" ON engagement_state FOR ALL TO public USING ((SELECT auth.role() AS role) = 'service_role'::text);
CREATE POLICY "Users can view own engagement state" ON engagement_state FOR SELECT TO public USING (user_id = (SELECT auth.uid() AS uid));

-- error_logs
CREATE POLICY "error_logs_service_role_only" ON error_logs FOR ALL TO public USING (auth.role() = 'service_role'::text);

-- generated_prompts
CREATE POLICY "Admin sees all prompts" ON generated_prompts FOR SELECT TO public USING (is_admin());
CREATE POLICY "Users can read own prompts" ON generated_prompts FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "Users see own prompts" ON generated_prompts FOR SELECT TO public USING ((SELECT auth.uid() AS uid) = user_id);

-- job_executions
CREATE POLICY "Admins can read job_executions" ON job_executions FOR SELECT TO public USING (is_admin());
CREATE POLICY "Service role full access job_executions" ON job_executions FOR ALL TO service_role USING (true) WITH CHECK (true);

-- memory_facts
CREATE POLICY "memory_facts_service_role" ON memory_facts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "memory_facts_user_delete" ON memory_facts FOR DELETE TO public USING (auth.uid() = user_id);
CREATE POLICY "memory_facts_user_insert" ON memory_facts FOR INSERT TO public WITH CHECK (auth.uid() = user_id);
CREATE POLICY "memory_facts_user_select" ON memory_facts FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "memory_facts_user_update" ON memory_facts FOR UPDATE TO public USING (auth.uid() = user_id);

-- message_embeddings
CREATE POLICY "Service role full access message_embeddings" ON message_embeddings FOR ALL TO service_role USING (true);
CREATE POLICY "message_embeddings_own_data" ON message_embeddings FOR ALL TO public USING (user_id = (SELECT auth.uid() AS uid)) WITH CHECK (user_id = (SELECT auth.uid() AS uid));

-- nikita_emotional_states
CREATE POLICY "Service role full access to emotional states" ON nikita_emotional_states FOR ALL TO public USING (auth.role() = 'service_role'::text) WITH CHECK (auth.role() = 'service_role'::text);
CREATE POLICY "Users can insert own emotional states" ON nikita_emotional_states FOR INSERT TO public WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own emotional states" ON nikita_emotional_states FOR UPDATE TO public USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can view own emotional states" ON nikita_emotional_states FOR SELECT TO public USING (auth.uid() = user_id);

-- nikita_entities
CREATE POLICY "Service role only entities" ON nikita_entities FOR ALL TO service_role USING (true) WITH CHECK (true);

-- nikita_life_events
CREATE POLICY "Service role only life_events" ON nikita_life_events FOR ALL TO service_role USING (true) WITH CHECK (true);

-- nikita_narrative_arcs
CREATE POLICY "Service role only narrative_arcs" ON nikita_narrative_arcs FOR ALL TO service_role USING (true) WITH CHECK (true);

-- nikita_thoughts
CREATE POLICY "Service role full access thoughts" ON nikita_thoughts FOR ALL TO public USING ((SELECT auth.role() AS role) = 'service_role'::text);
CREATE POLICY "Users can view own thoughts" ON nikita_thoughts FOR SELECT TO public USING ((SELECT auth.uid() AS uid) = user_id);

-- onboarding_states
CREATE POLICY "Admins can view all onboarding states" ON onboarding_states FOR SELECT TO public USING (is_admin());
CREATE POLICY "Service role can manage onboarding states" ON onboarding_states FOR ALL TO service_role USING (true);

-- pending_registrations
CREATE POLICY "Admins can read pending_registrations" ON pending_registrations FOR SELECT TO public USING (is_admin());
CREATE POLICY "Service role full access pending_registrations" ON pending_registrations FOR ALL TO service_role USING (true) WITH CHECK (true);

-- psyche_states
CREATE POLICY "Service role full access" ON psyche_states FOR ALL TO public USING ((SELECT auth.role() AS role) = 'service_role'::text);
CREATE POLICY "Users can read own psyche state" ON psyche_states FOR SELECT TO public USING ((SELECT auth.uid() AS uid) = user_id);

-- push_subscriptions
CREATE POLICY "Users manage own push subscriptions" ON push_subscriptions FOR ALL TO public USING (auth.uid() = user_id);
CREATE POLICY "push_subscriptions_service_role_only" ON push_subscriptions FOR ALL TO public USING (auth.role() = 'service_role'::text);

-- ready_prompts
CREATE POLICY "ready_prompts_service_role" ON ready_prompts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "ready_prompts_user_delete" ON ready_prompts FOR DELETE TO public USING (auth.uid() = user_id);
CREATE POLICY "ready_prompts_user_insert" ON ready_prompts FOR INSERT TO public WITH CHECK (auth.uid() = user_id);
CREATE POLICY "ready_prompts_user_select" ON ready_prompts FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "ready_prompts_user_update" ON ready_prompts FOR UPDATE TO public USING (auth.uid() = user_id);

-- scheduled_events
CREATE POLICY "Users can view their own events" ON scheduled_events FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "scheduled_events_service_role_only" ON scheduled_events FOR ALL TO public USING (auth.role() = 'service_role'::text);

-- scheduled_touchpoints
CREATE POLICY "Service role only touchpoints" ON scheduled_touchpoints FOR ALL TO service_role USING (true) WITH CHECK (true);

-- score_history
CREATE POLICY "Admin reads all score_history" ON score_history FOR SELECT TO public USING (((SELECT (auth.uid() = score_history_1.user_id) FROM score_history score_history_1 WHERE (score_history_1.id = score_history_1.id)) OR is_admin()));
CREATE POLICY "Service role full access score_history" ON score_history FOR ALL TO service_role USING (true);
CREATE POLICY "score_history_own_data" ON score_history FOR ALL TO public USING (user_id = (SELECT auth.uid() AS uid)) WITH CHECK (user_id = (SELECT auth.uid() AS uid));

-- user_backstories
CREATE POLICY "Admins can view all backstories" ON user_backstories FOR SELECT TO public USING (is_admin());
CREATE POLICY "Users can delete own backstory" ON user_backstories FOR DELETE TO public USING (user_id = auth.uid());
CREATE POLICY "Users can insert own backstory" ON user_backstories FOR INSERT TO public WITH CHECK (user_id = (SELECT auth.uid() AS uid));
CREATE POLICY "Users can update own backstory" ON user_backstories FOR UPDATE TO public USING (user_id = (SELECT auth.uid() AS uid));
CREATE POLICY "Users can view own backstory" ON user_backstories FOR SELECT TO public USING (user_id = (SELECT auth.uid() AS uid));

-- user_metrics
CREATE POLICY "Admin reads all metrics" ON user_metrics FOR SELECT TO public USING (((SELECT (auth.uid() = user_metrics_1.user_id) FROM user_metrics user_metrics_1 WHERE (user_metrics_1.id = user_metrics_1.id)) OR is_admin()));
CREATE POLICY "Service role full access user_metrics" ON user_metrics FOR ALL TO service_role USING (true);
CREATE POLICY "Users can read own metrics" ON user_metrics FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "user_metrics_own_data" ON user_metrics FOR ALL TO public USING (user_id = (SELECT auth.uid() AS uid)) WITH CHECK (user_id = (SELECT auth.uid() AS uid));

-- user_narrative_arcs
CREATE POLICY "user_narrative_arcs_delete_own" ON user_narrative_arcs FOR DELETE TO public USING (auth.uid() = user_id);
CREATE POLICY "user_narrative_arcs_insert_own" ON user_narrative_arcs FOR INSERT TO public WITH CHECK (auth.uid() = user_id);
CREATE POLICY "user_narrative_arcs_select_own" ON user_narrative_arcs FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "user_narrative_arcs_update_own" ON user_narrative_arcs FOR UPDATE TO public USING (auth.uid() = user_id);

-- user_profiles
CREATE POLICY "Admins can view all profiles" ON user_profiles FOR SELECT TO public USING (is_admin());
CREATE POLICY "Users can delete own profile" ON user_profiles FOR DELETE TO public USING (id = auth.uid());
CREATE POLICY "Users can insert own profile" ON user_profiles FOR INSERT TO public WITH CHECK (id = (SELECT auth.uid() AS uid));
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE TO public USING (id = (SELECT auth.uid() AS uid));
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT TO public USING (id = (SELECT auth.uid() AS uid));

-- user_social_circles
CREATE POLICY "user_social_circles_delete_own" ON user_social_circles FOR DELETE TO public USING (auth.uid() = user_id);
CREATE POLICY "user_social_circles_insert_own" ON user_social_circles FOR INSERT TO public WITH CHECK (auth.uid() = user_id);
CREATE POLICY "user_social_circles_select_own" ON user_social_circles FOR SELECT TO public USING (auth.uid() = user_id);
CREATE POLICY "user_social_circles_update_own" ON user_social_circles FOR UPDATE TO public USING (auth.uid() = user_id);

-- user_vice_preferences
CREATE POLICY "Admin reads all user_vice_preferences" ON user_vice_preferences FOR SELECT TO public USING (((SELECT (auth.uid() = user_vice_preferences_1.user_id) FROM user_vice_preferences user_vice_preferences_1 WHERE (user_vice_preferences_1.id = user_vice_preferences_1.id)) OR is_admin()));
CREATE POLICY "Service role full access user_vice_preferences" ON user_vice_preferences FOR ALL TO service_role USING (true);
CREATE POLICY "vice_preferences_own_data" ON user_vice_preferences FOR ALL TO public USING (user_id = (SELECT auth.uid() AS uid)) WITH CHECK (user_id = (SELECT auth.uid() AS uid));

-- users
CREATE POLICY "Admin reads all users" ON users FOR SELECT TO public USING (((SELECT auth.uid() AS uid) = id) OR is_admin());
CREATE POLICY "Admin updates users" ON users FOR UPDATE TO public USING (is_admin());
CREATE POLICY "Service role full access users" ON users FOR ALL TO service_role USING (true);
CREATE POLICY "Users can read own data" ON users FOR SELECT TO public USING (auth.uid() = id);
CREATE POLICY "Users can update own data" ON users FOR UPDATE TO public USING (auth.uid() = id);
CREATE POLICY "users_own_data" ON users FOR ALL TO public USING (id = (SELECT auth.uid() AS uid)) WITH CHECK (id = (SELECT auth.uid() AS uid));

-- venue_cache
CREATE POLICY "Anyone can read venue cache" ON venue_cache FOR SELECT TO authenticated USING (true);
CREATE POLICY "Service role can manage venue cache" ON venue_cache FOR ALL TO service_role USING (true);

-- voice_calls
CREATE POLICY "voice_calls_service_role_only" ON voice_calls FOR ALL TO public USING (auth.role() = 'service_role'::text);

-- ============================================================================
-- TRIGGERS
-- ============================================================================
CREATE TRIGGER update_onboarding_states_updated_at BEFORE UPDATE ON onboarding_states FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_backstories_updated_at BEFORE UPDATE ON user_backstories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_metrics_updated_at BEFORE UPDATE ON user_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
