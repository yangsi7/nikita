-- Baseline Schema for Nikita Database
-- Generated: 2026-02-23 from production Supabase instance
-- Captures all 85 migrations as a single reproducible baseline.
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
-- RLS (Row Level Security)
-- ============================================================================
-- RLS is enabled on all user-facing tables.
-- Service role bypasses RLS for backend operations.
-- See individual migration files for policy details.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_vice_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE nikita_thoughts ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ready_prompts ENABLE ROW LEVEL SECURITY;
