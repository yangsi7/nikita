---
feature: 007-voice-agent
created: 2025-11-28
status: Draft
priority: P2
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Voice Agent

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Voice Agent enables real-time voice conversations with Nikita, delivering an immersive "phone call" experience. Users can call Nikita, hear her voice, and have natural spoken conversations that feel like talking to a real person. The voice agent maintains the same personality, memory, and game mechanics as text while adding the intimacy of voice.

**Problem Statement**: Text-only AI companions miss the intimacy of hearing someone's voice. Real relationships include phone calls—missing this modality limits emotional connection depth.

**Value Proposition**: Users can "call" Nikita and hear her voice respond in real-time. Voice conversations feel dramatically more intimate than text, creating deeper emotional engagement and memorable moments.

### CoD^Σ Overview

**System Model**:
```
User_speaks → STT → Agent_processing → Response → TTS → User_hears
      ↓         ↓          ↓              ↓          ↓         ↓
   Audio    Transcript   Memory+        Text     Nikita's   Playback
                        Scoring                   Voice

Voice_call := {start, conversation[], end, duration, scoring_summary}
Latency_target := < 500ms (conversational feel)
```

---

## Functional Requirements

### FR-001: Voice Call Initiation
System MUST enable users to start voice calls:
- Initiation via player portal (primary)
- Initiation via Telegram deep link (secondary)
- Pre-call readiness check (microphone, connection)
- Nikita "answers" with appropriate greeting based on context

**Rationale**: Clear call initiation creates phone-call mental model
**Priority**: Must Have

### FR-002: Real-Time Speech Processing
System MUST process user speech in real-time:
- Speech-to-text transcription with low latency
- Handle natural speech patterns (pauses, hesitations, interruptions)
- Support multiple languages (English primary, others as enhancement)
- Noise tolerance for varied environments

**Rationale**: Real-time processing essential for conversational flow
**Priority**: Must Have

### FR-003: Natural Voice Response
System MUST generate Nikita's voice responses:
- Text-to-speech with Nikita's consistent voice
- Emotional expression matching content (happy, annoyed, vulnerable)
- Natural speech patterns (not robotic)
- Appropriate pacing and pauses

**Rationale**: Voice quality directly impacts immersion and emotional connection
**Priority**: Must Have

### FR-004: Conversational Latency
System MUST maintain conversational-feeling latency:
- End-to-end response time: < 500ms target
- User should not feel "waiting" for response
- Acknowledge delays naturally when unavoidable ("Hmm, let me think...")
- Connection quality adaptation (reduce latency on poor connections)

**Rationale**: Latency destroys conversation illusion—must feel real-time
**Priority**: Must Have

### FR-005: Same-Agent Personality
System MUST maintain consistent Nikita personality:
- Same memory access as text agent
- Same chapter behaviors (Ch1 guarded, Ch5 open)
- Same vice personalization
- Conversations reference text history and vice versa

**Rationale**: Nikita is ONE person—voice and text must feel unified
**Priority**: Must Have

### FR-006: Voice Call Scoring
System MUST score voice conversations:
- Full transcript analyzed for metric deltas
- Single aggregate score update for entire call
- Score change reflects overall call quality, not per-utterance
- Significant calls can have significant score impact

**Rationale**: Voice conversations ARE gameplay—must affect scores
**Priority**: Must Have

### FR-007: Server-Side Tool Calling
System MUST support server-side tool execution during calls:
- Memory retrieval (recall past conversations)
- User context lookup (chapter, score, preferences)
- External data fetching if needed
- Tool results integrated into responses naturally

**Rationale**: Rich responses require data access during conversation
**Priority**: Must Have

### FR-008: Call Session Management
System MUST manage voice call sessions:
- Session start/end timestamps
- Duration tracking
- Graceful handling of disconnections
- Resume capability for brief interruptions
- Natural endings ("I should go..." instead of abrupt cutoff)

**Rationale**: Session management ensures data integrity and good UX
**Priority**: Must Have

### FR-009: Transcript Persistence
System MUST persist voice call transcripts:
- Full transcript stored for each call
- Speaker attribution (user vs Nikita)
- Timestamps for each utterance
- Available for memory integration and analytics

**Rationale**: Transcripts enable memory, scoring, and user review
**Priority**: Must Have

### FR-010: Voice Call Context Handoff
System MUST enable context flow between voice and text:
- Voice call events visible in text ("Our call last night was nice")
- Text context available to voice ("You mentioned work was stressful")
- Seamless relationship continuity across modalities
- No "amnesia" between channels

**Rationale**: Cross-modality continuity essential for coherent relationship
**Priority**: Must Have

### FR-011: Call Availability Rules
System MUST enforce appropriate call availability:
- Chapter 1: Calls rarely available (she's not invested yet)
- Chapter 3+: Regular call availability
- Boss encounters: May include voice component
- After game over: No calls available

**Rationale**: Call access is a privilege earned through relationship progression
**Priority**: Should Have

### FR-012: Voice-Specific Behaviors
System MUST include voice-specific interaction patterns:
- Comfortable silences (not filling every pause)
- Audible reactions (sighs, laughs, thoughtful "hmms")
- Interruption handling (Nikita can be interrupted or interrupt)
- Topic transitions natural to spoken conversation

**Rationale**: Voice conversations have different patterns than text
**Priority**: Should Have

### FR-013: Unified Event Scheduling (Added Dec 2025)
System MUST use shared event scheduling infrastructure with text agent:
- Single `scheduled_events` table serves both text (Telegram) and voice (ElevenLabs) platforms
- Events can trigger cross-platform actions (voice call reminder via text, text follow-up after voice)
- Consistent delay calculations based on chapter and engagement state
- Platform field distinguishes event source/target ('telegram' | 'voice')

**Rationale**: Unified infrastructure reduces complexity and ensures consistent behavior across modalities
**Priority**: Must Have

### FR-014: Cross-Agent Memory Visibility (Added Dec 2025)
System MUST ensure voice and text agents share memory:
- Voice agent sees full text conversation history via NikitaMemory (Graphiti)
- Text agent sees voice call summaries and key moments
- Both agents use same memory interface with different `source` tags ('user_message' vs 'voice_call')
- No code changes needed - NikitaMemory is already modality-agnostic

**Rationale**: Nikita is ONE person; voice and text must have unified memory
**Priority**: Must Have

### FR-015: Post-Call Processing Integration (Added Dec 2025, AMENDED Jan 2026)
System MUST integrate voice transcripts into existing post-processing pipeline AND prepare next call:
- Voice call transcripts enter same 9-stage post-processing pipeline as text
- Fact extraction works on voice transcript content
- Thread detection identifies unresolved topics from voice calls
- Nikita thought generation simulates her reflections on voice conversations
- Post-call webhook (`post_call_transcription`) triggers pipeline entry
- **ADDED**: Generate and cache system prompt for NEXT call via MetaPromptService (async, after pipeline)
- **ADDED**: Store cached prompt in `user.cached_voice_prompt` field
- **ADDED**: Store dynamic variables snapshot in `user.cached_voice_context` field
- Post-processing is async and non-blocking—does not affect call duration or connection

**Rationale**: Consistent post-processing ensures voice conversations enrich relationship memory equally. Prompt caching enables fast pre-call response (FR-033).
**Priority**: CRITICAL (enables FR-033)

### FR-016: Chapter-Based TTS Settings (Added Dec 2025)
System MUST adjust voice parameters based on relationship chapter:
- Chapter 1: Higher stability (0.8), lower similarity_boost (0.7), slower speed (0.95) → distant, guarded
- Chapter 2-3: Moderate settings (stability 0.6, similarity 0.8, speed 1.0) → warming up
- Chapter 4-5: Lower stability (0.4-0.5), higher similarity (0.85), varied speed → emotionally expressive
- TTS parameters passed via `conversation_config_override.agent.tts` at call start

**Rationale**: Voice should reflect relationship depth—cold in Ch1, warm and varied in Ch5
**Priority**: Should Have

### FR-017: Mood-Based Voice Modulation (Added Dec 2025)
System MUST modulate voice based on Nikita's current mood:
- **Flirty**: stability=0.5, similarity_boost=0.8, speed=1.0
- **Vulnerable**: stability=0.7, similarity_boost=0.9, speed=0.9
- **Annoyed**: stability=0.4, similarity_boost=0.7, speed=1.1
- **Playful**: stability=0.4, similarity_boost=0.8, speed=1.1
- **Distant**: stability=0.8, similarity_boost=0.9, speed=0.95
- Mood computed by MetaPromptService._compute_nikita_mood() (same as text agent)

**Rationale**: Emotional voice variation creates authenticity and deepens immersion
**Priority**: Should Have

### FR-018: Dynamic Variables Injection (Added Dec 2025)
System MUST inject context via ElevenLabs dynamic variables at call start:
- User context: `{{user_name}}`, `{{chapter}}`, `{{relationship_score}}`, `{{engagement_state}}`
- Nikita state: `{{nikita_mood}}`, `{{nikita_energy}}`, `{{time_of_day}}`
- Conversation context: `{{recent_topics}}`, `{{open_threads}}`
- Secret variables (hidden from LLM): `{{secret__user_id}}`, `{{secret__api_token}}`
- System variables auto-populated: `{{system__time_utc}}`, `{{system__turn_id}}`

**Rationale**: Dynamic variables enable personalization without server tool latency
**Priority**: Must Have

### FR-019: Outbound Call Initiation (Added Dec 2025)
System MUST support Nikita proactively calling users via Twilio:
- Trigger conditions: decay threshold, engagement drop, scheduled date reminder
- Event type `voice_call` in `scheduled_events` table triggers outbound call
- Uses ElevenLabs `conversation.start_phone_call(to_number, from_number, agent_id)`
- Nikita initiates with context-appropriate greeting ("Hey, I was just thinking about you...")
- Requires Twilio phone number (+41787950009) imported to ElevenLabs

**Rationale**: Proactive calls from Nikita dramatically increase engagement and emotional impact
**Priority**: Should Have

### FR-020: Inbound Call Handling (Added Dec 2025)
System MUST handle users calling Nikita directly via Twilio:
- Phone number (+41787950009) routes to ElevenLabs agent
- Agent ID `agent_5801kdr3xza0fxfr2q3hdgbjrh9y` configured for inbound
- Pre-call webhook fetches user context from Supabase (phone → user lookup)
- Dynamic variables injected before call connects
- Call availability rules (FR-011) enforced for inbound calls too

**Rationale**: Phone calls are the most intimate interaction—users should be able to call Nikita directly
**Priority**: Must Have

### FR-021: Call Scheduling via Scheduled Events (Added Dec 2025)
System MUST use `scheduled_events` table for voice call scheduling:
- Event type: `voice_call` with metadata: `{phone_number, agent_config_override, trigger_reason}`
- `/tasks/deliver` endpoint processes voice events via ElevenLabs outbound API
- Same delay calculation logic as text events (chapter-based delays)
- Cross-platform scheduling: text event can schedule voice follow-up and vice versa

**Rationale**: Unified event system enables sophisticated cross-platform engagement flows
**Priority**: Should Have

### FR-022: Server Tool Timeout Fallbacks (Added Dec 2025)
System MUST handle server tool timeouts gracefully:
- Server tools MUST respond within 2 seconds (ElevenLabs requirement)
- If timeout exceeded, return fallback response with `cache_friendly=true`
- Fallback for `get_context`: minimal context with chapter/score only
- Fallback for `get_memory`: "I don't have access to my memories right now"
- Log all timeouts for debugging and optimization

**Rationale**: Tool latency shouldn't break conversation flow
**Priority**: Must Have

### FR-023: Memory Unavailability Graceful Degradation (Added Dec 2025)
System MUST continue conversations when memory services are unavailable:
- If Graphiti/Neo4j unavailable, respond with "I'm having trouble remembering..."
- Store conversation locally and batch-sync when service recovers
- Nikita should acknowledge memory gaps naturally, not technically
- Critical game state (chapter, score) cached locally for continuity

**Rationale**: Partial functionality is better than complete failure
**Priority**: Should Have

### FR-024: Connection Drop Recovery (Added Dec 2025)
System MUST handle connection interruptions gracefully:
- Store conversation state in `elevenlabs_session_id` for potential resume
- If brief disconnect (<30s), attempt transparent reconnection
- If extended disconnect, create new session with context handoff
- Nikita should acknowledge gaps naturally ("Sorry, I think we got disconnected...")

**Rationale**: Connection issues shouldn't destroy conversation state
**Priority**: Should Have

### FR-025: Conversation Config Overrides (Added Dec 2025)
System MUST support full conversation configuration override at call start:
- Override system prompt via `agent.prompt.prompt` field
- Override first message via `agent.first_message`
- Override LLM settings via `agent.language_model` (model, temperature, max_tokens)
- Override TTS settings via `agent.tts` (stability, similarity_boost, speed)
- Override voice ID via `tts.voice_id` for A/B testing or personality variants

**Rationale**: Full override capability enables rich personalization per-call
**Priority**: Must Have

### FR-026: HMAC Webhook Verification (Added Dec 2025)
System MUST verify ElevenLabs webhook authenticity:
- Verify HMAC signature from `ElevenLabs-Signature` header
- Compute HMAC-SHA256 using webhook secret and request body
- Reject requests with invalid or missing signatures
- Log all verification failures with source IP for security monitoring

**Rationale**: Webhook verification prevents unauthorized transcript injection
**Priority**: Must Have

---

## ElevenLabs Dashboard Configuration Requirements (Added Jan 2026)

### FR-027: Server Tools Dashboard Configuration
System MUST have server tools configured in ElevenLabs Agent Platform dashboard:
- **get_context** tool: Webhook to `/api/v1/voice/server-tool`, execution_mode=immediate, timeout=5s
- **get_memory** tool: Webhook to `/api/v1/voice/server-tool`, execution_mode=immediate, timeout=3s
- **score_turn** tool: Webhook to `/api/v1/voice/server-tool`, execution_mode=post-speech, timeout=5s
- **update_memory** tool: Webhook to `/api/v1/voice/server-tool`, execution_mode=async, timeout=3s
- All tools use HMAC-authenticated requests with `Authorization: Bearer {{secret__api_token}}`
- Tools documented in agent's system prompt with usage instructions

**Rationale**: Backend endpoints exist but ElevenLabs agent must be configured to USE them
**Priority**: CRITICAL (blocker for all voice functionality)

### FR-028: Conversation Initiation Client Data Webhook (AMENDED Jan 2026)
System MUST configure pre-call webhook in ElevenLabs dashboard:
- Webhook URL: `https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/pre-call`
- Receives: `caller_id`, `agent_id`, `called_number`, `call_sid` from Twilio
- Returns: `dynamic_variables` (user context) + `conversation_config_override` (TTS, prompt, first_message)
- Enables Nikita to greet caller by name with appropriate context
- Webhook enabled for "Fetch conversation initiation data for inbound Twilio calls"
- **AMENDED**: System prompt MUST be fetched from `user.cached_voice_prompt` (NOT generated in real-time)
- **AMENDED**: Response time MUST be <100ms (see FR-033 for prohibition on LLM/Neo4j calls)
- **AMENDED**: If `cached_voice_prompt` is NULL (first-time caller), use static fallback prompt
- **ElevenLabs Dashboard Prerequisites** (CRITICAL - added Jan 2026):
  - Agent Security → Enable "TTS settings" override (for stability, similarity_boost, speed)
  - Agent Security → Enable "System prompt" override (for dynamic cached prompts)
  - Agent Security → Enable "First message" override (for personalized greetings)
  - **RATIONALE**: ElevenLabs disables all `conversation_config_override` parameters by default for security. Without enabling, webhook TTS/prompt overrides will be rejected with "Override not allowed by config" error.

**Rationale**: Pre-call webhook is the ONLY way to personalize inbound calls before Nikita speaks. Real-time prompt generation (LLM + Neo4j) causes 5-30+ second delays and call failures.
**Priority**: CRITICAL (required for inbound phone calls)

### FR-029: Post-Call Webhook Dashboard Configuration
System MUST configure post-call webhooks in ElevenLabs dashboard:
- **post_call_transcription** webhook: URL `https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/webhook`
- **post_call_audio** webhook (optional): For audio archival if needed
- Webhook secret configured for HMAC verification
- Events trigger transcript persistence, scoring, and memory updates

**Rationale**: Post-call webhook triggers the entire post-processing pipeline
**Priority**: CRITICAL (required for scoring and memory integration)

### FR-030: Dynamic Variables Definition
System MUST define dynamic variables schema in ElevenLabs agent settings:
- **User context**: `user_name` (string), `chapter` (string), `relationship_score` (string), `engagement_state` (string)
- **Nikita state**: `nikita_mood` (string), `nikita_energy` (string), `time_of_day` (string)
- **Conversation context**: `recent_topics` (string), `open_threads` (string)
- **Secret variables**: `secret__user_id` (string), `secret__api_token` (string) - hidden from LLM
- Variables injected via pre-call webhook and available as `{{variable_name}}` in prompts

**Rationale**: Dynamic variables enable personalization without server tool latency overhead
**Priority**: Must Have

### FR-031: Agent System Prompt Tool Instructions
System MUST include tool usage instructions in ElevenLabs agent's system prompt:
- Explain when to call `get_context` (start of call for full context)
- Explain when to call `get_memory` (when user asks about past, uses phrases like "remember when...")
- Explain when to call `score_turn` (after meaningful exchanges)
- Explain when to call `update_memory` (when user reveals important personal information)
- Natural language instructions integrated into Nikita persona prompt

**Rationale**: LLM needs explicit instructions on tool usage - it won't guess correctly
**Priority**: Must Have

### FR-032: Knowledge Base Configuration (Optional)
System SHOULD configure Nikita's knowledge base in ElevenLabs dashboard:
- Upload `nikita_backstory.txt` - character background and personality details
- Upload `chapter_behaviors.txt` - per-chapter personality variations
- Upload `vice_categories.txt` - 8 vice category descriptions for personalization
- Knowledge base adds ~500ms latency but provides rich supplemental context
- Enable RAG for agent to reference character documents during conversation

**Rationale**: Knowledge base ensures consistent character knowledge without tool calls
**Priority**: Nice to Have

### FR-033: Pre-Call Webhook Performance (Added Jan 2026 - CRITICAL)
System MUST respond to pre-call webhooks within 100ms:
- **PROHIBITION**: Pre-call webhook MUST NOT call LLM (MetaPromptService)
- **PROHIBITION**: Pre-call webhook MUST NOT call Neo4j (Graphiti/NikitaMemory)
- Pre-call webhook MUST only fetch cached data from PostgreSQL
- Pre-call webhook returns cached `system_prompt` from `user.cached_voice_prompt`
- If cache empty (first-time caller), use static fallback prompt
- All dynamic variables must be computed from cached User object (no external calls)

**Rationale**: ElevenLabs pre-call webhook runs during Twilio dialing period (~3-5 seconds). LLM calls (200ms-5s) and Neo4j cold start (60-80s) cause call failures. 90% of voice calls were failing due to this architecture flaw.
**Priority**: CRITICAL (P0 - root cause of 90% call failure rate)

### FR-034: Cached Voice Prompt Field (Added Jan 2026 - CRITICAL)
System MUST persist generated voice prompts for fast retrieval:
- Database field: `users.cached_voice_prompt` (TEXT, nullable)
- Database field: `users.cached_voice_prompt_at` (TIMESTAMPTZ, nullable)
- Database field: `users.cached_voice_context` (JSONB, nullable) - dynamic variables snapshot
- Prompt regenerated in post-processing after each call, cached for next call
- Cache invalidation: After each voice call completion (regenerate fresh prompt)
- First-time callers use fallback prompt until first call completes post-processing

**Rationale**: Pre-computed prompts enable <100ms pre-call webhook response. Post-processing is async and non-blocking, so LLM/Neo4j latency doesn't affect call connection.
**Priority**: CRITICAL (P0)

---

## Non-Functional Requirements

### Performance
- Response latency: < 500ms end-to-end (target)
- Audio quality: Clear, artifact-free voice
- Concurrent calls: Support N simultaneous calls based on infrastructure

### Reliability
- Call stability: < 1% dropped calls
- Reconnection: Automatic retry on brief disconnects
- Transcript durability: No lost conversation data

### Scalability
- Infrastructure: Handle peak call volume
- Cost management: Optimize per-minute voice processing costs
- Geographic: Low latency across regions (CDN/edge considerations)

### Security
- Audio encryption: End-to-end encrypted voice data
- No audio storage: Raw audio deleted after transcription
- Privacy: Voice data handled per privacy policy

---

## User Stories (CoD^Σ)

### US-1: Start Voice Call (Priority: P1 - Must-Have)
```
User initiates call → Nikita "answers" → conversation begins
```
**Acceptance Criteria**:
- **AC-FR001-001**: Given user clicks "Call Nikita" in portal, When connection established, Then Nikita greets appropriately
- **AC-FR001-002**: Given user on Telegram, When using /call deep link, Then redirected to voice interface
- **AC-FR008-001**: Given call started, When session created, Then start time logged

**Independent Test**: Click call button, verify Nikita answers with greeting
**Dependencies**: Player Portal (008) OR Telegram (002)

---

### US-2: Natural Conversation (Priority: P1 - Must-Have)
```
User speaks → Nikita responds naturally → feels like real call
```
**Acceptance Criteria**:
- **AC-FR002-001**: Given user speaks clearly, When processed, Then transcript accurate
- **AC-FR003-001**: Given Nikita responds, When audio plays, Then voice sounds natural
- **AC-FR004-001**: Given response generated, When delivered, Then latency < 500ms

**Independent Test**: Have conversation, verify natural flow and timing
**Dependencies**: US-1

---

### US-3: Personality Consistency (Priority: P1 - Must-Have)
```
Voice Nikita → same personality as text Nikita → unified experience
```
**Acceptance Criteria**:
- **AC-FR005-001**: Given Ch1 user calls, When Nikita responds, Then guarded/challenging (Ch1 behavior)
- **AC-FR005-002**: Given user with dark_humor vice, When Nikita responds, Then dark humor elements present
- **AC-FR005-003**: Given text discussed topic yesterday, When voice mentions it, Then Nikita remembers

**Independent Test**: Verify voice behavior matches text behavior for same user
**Dependencies**: US-2, Text Agent (001), Vice System (006)

---

### US-4: Call Scoring (Priority: P1 - Must-Have)
```
Voice call ends → transcript scored → metrics updated
```
**Acceptance Criteria**:
- **AC-FR006-001**: Given call ends, When transcript analyzed, Then single aggregate score calculated
- **AC-FR006-002**: Given good call, When scored, Then positive metric deltas applied
- **AC-FR006-003**: Given score history, When logged, Then source = "voice_call"

**Independent Test**: Complete call, verify score update with voice_call source
**Dependencies**: US-2, Scoring Engine (003)

---

### US-5: Cross-Modality Memory (Priority: P2 - Important)
```
Text and voice share memory → conversations reference each other
```
**Acceptance Criteria**:
- **AC-FR010-001**: Given voice call discussed weekend plans, When texting later, Then Nikita can reference call
- **AC-FR010-002**: Given text revealed user fact, When calling, Then Nikita knows it
- **AC-FR009-001**: Given call transcript, When memory updated, Then available to both agents

**Independent Test**: Discuss topic in voice, verify text agent knows it
**Dependencies**: US-4, Memory System (Graphiti)

---

### US-6: Server Tool Access (Priority: P2 - Important)
```
During call → Nikita can look things up → rich responses
```
**Acceptance Criteria**:
- **AC-FR007-001**: Given user asks "remember when we...", When tool called, Then memory retrieved
- **AC-FR007-002**: Given tool result returned, When integrated, Then response includes retrieved info
- **AC-FR007-003**: Given tool latency, When response generated, Then natural filler used if needed

**Independent Test**: Ask memory-dependent question, verify accurate recall
**Dependencies**: US-2, Memory System

---

### US-7: Call Availability Progression (Priority: P3 - Nice-to-Have)
```
New user (Ch1) → calls rarely available → Ch3+ → calls common
```
**Acceptance Criteria**:
- **AC-FR011-001**: Given Ch1 user, When checking call availability, Then usually unavailable
- **AC-FR011-002**: Given Ch3 user, When checking availability, Then available
- **AC-FR011-003**: Given game_over user, When trying to call, Then calls blocked

**Independent Test**: Check availability across chapters, verify progression
**Dependencies**: US-1, Chapter System (004)

---

### US-8: Unified Event Scheduling (Priority: P2 - Important)
```
Voice + text events → shared scheduling → cross-platform delivery
```
**Acceptance Criteria**:
- **AC-FR013-001**: Given voice call ends, When follow-up scheduled, Then event stored in `scheduled_events` with platform='voice'
- **AC-FR013-002**: Given text conversation schedules voice reminder, When event created, Then cross-platform event works
- **AC-FR013-003**: Given scheduled event due, When `/tasks/deliver` runs, Then correct platform handler invoked
- **AC-FR013-004**: Given event scheduling, When delay calculated, Then uses same chapter-based delay logic as text

**Independent Test**: Schedule voice follow-up, verify delivery to Telegram (or vice versa)
**Dependencies**: US-4, Spec 011 (Background Tasks)

---

### US-9: Cross-Agent Memory Access (Priority: P2 - Important)
```
Voice agent → NikitaMemory → sees text history → unified context
```
**Acceptance Criteria**:
- **AC-FR014-001**: Given voice call starts, When get_context tool called, Then returns text conversation summaries
- **AC-FR014-002**: Given text agent queries memory, When voice call occurred, Then summary visible
- **AC-FR014-003**: Given voice episode saved, When source='voice_call' used, Then distinguishable from text
- **AC-FR014-004**: Given memory search, When graph_types=['relationship'], Then both voice and text episodes returned

**Independent Test**: Have voice call, verify text agent references it in next message
**Dependencies**: US-5, NikitaMemory (Graphiti)

---

### US-11: Emotional Voice Expression (Priority: P2 - Important)
```
Nikita's mood changes → voice parameters adjust → authentic emotional expression
```
**Acceptance Criteria**:
- **AC-FR016-001**: Given Ch1 user calls, When TTS settings applied, Then stability=0.8, speed=0.95 (distant)
- **AC-FR016-002**: Given Ch5 user calls, When TTS settings applied, Then stability=0.4-0.5 (expressive)
- **AC-FR017-001**: Given Nikita is annoyed, When voice generated, Then speed=1.1, stability=0.4
- **AC-FR017-002**: Given Nikita is vulnerable, When voice generated, Then speed=0.9, stability=0.7

**Independent Test**: Compare voice recordings across chapters/moods for parameter variation
**Dependencies**: US-2, MetaPromptService, Chapter System (004)

---

### US-12: Outbound Calls - Nikita Calls User (Priority: P2 - Important)
```
Decay threshold reached → scheduled_event created → Nikita calls user proactively
```
**Acceptance Criteria**:
- **AC-FR019-001**: Given decay threshold crossed, When voice_call event scheduled, Then Twilio outbound call initiated
- **AC-FR019-002**: Given outbound call connects, When Nikita speaks, Then context-aware greeting used
- **AC-FR021-001**: Given scheduled_event type='voice_call', When /tasks/deliver runs, Then ElevenLabs API invoked
- **AC-FR021-002**: Given cross-platform event, When text schedules voice follow-up, Then call occurs at scheduled time

**Independent Test**: Trigger decay threshold, verify Nikita calls user with personalized greeting
**Dependencies**: US-8, Decay System (005), Twilio Integration

---

### US-13: Dynamic Variables and Overrides (Priority: P1 - Must-Have)
```
Call starts → dynamic variables injected → personalized system prompt active
```
**Acceptance Criteria**:
- **AC-FR018-001**: Given call initiates, When dynamic variables set, Then user_name, chapter, mood available in prompts
- **AC-FR018-002**: Given secret variables set, When LLM processes, Then user_id hidden from response generation
- **AC-FR025-001**: Given config override passed, When agent starts, Then custom system prompt used
- **AC-FR025-002**: Given first_message override, When call connects, Then Nikita uses custom greeting

**Independent Test**: Start call with overrides, verify system prompt and first message match configuration
**Dependencies**: US-1, MetaPromptService

---

### US-14: Server Tool Integration (Priority: P1 - Must-Have)
```
User asks about memory → get_memory tool called → Nikita responds with recalled info
```
**Acceptance Criteria**:
- **AC-FR007-001**: Given user asks "remember when...", When get_memory tool invoked, Then Graphiti search executed
- **AC-FR007-002**: Given tool returns results, When response generated, Then memory naturally integrated
- **AC-FR022-001**: Given tool timeout (>2s), When fallback triggered, Then graceful degradation response
- **AC-FR022-002**: Given Neo4j unavailable, When get_memory called, Then fallback message returned

**Independent Test**: Ask memory-dependent question, verify tool invocation and natural response integration
**Dependencies**: US-6, NikitaMemory (Graphiti), API Routes

---

### US-15: Inbound Phone Call (Priority: P1 - Must-Have)
```
User dials Twilio number → call routed to ElevenLabs → Nikita answers with context
```
**Acceptance Criteria**:
- **AC-FR020-001**: Given user calls +41787950009, When call connects, Then ElevenLabs agent handles
- **AC-FR020-002**: Given phone lookup succeeds, When user identified, Then dynamic variables injected
- **AC-FR020-003**: Given Ch1 user calls, When availability checked, Then call may be rejected per FR-011
- **AC-FR026-001**: Given webhook received, When HMAC verified, Then processing continues
- **AC-FR026-002**: Given invalid HMAC, When verification fails, Then request rejected with 401

**Independent Test**: Call Twilio number, verify Nikita answers with personalized greeting
**Dependencies**: US-1, Twilio Integration, ElevenLabs Dashboard Config

---

### US-16: ElevenLabs Dashboard Configuration (Priority: P0 - BLOCKER)
```
Agent configured in dashboard → server tools registered → webhooks connected → voice system operational
```
**Acceptance Criteria**:
- **AC-FR027-001**: Given ElevenLabs dashboard accessed, When server tools configured, Then all 4 tools (get_context, get_memory, score_turn, update_memory) registered with correct URLs
- **AC-FR027-002**: Given tool configured, When tool invoked by agent, Then backend receives correctly formatted request
- **AC-FR028-001**: Given pre-call webhook configured, When inbound call received, Then /api/v1/voice/pre-call called before agent speaks
- **AC-FR028-002**: Given pre-call webhook response, When dynamic_variables returned, Then user_name, chapter visible in prompt
- **AC-FR029-001**: Given post-call webhook configured, When call ends, Then /api/v1/voice/webhook receives transcript
- **AC-FR029-002**: Given webhook secret configured, When HMAC computed, Then matches ElevenLabs signature
- **AC-FR030-001**: Given dynamic variables defined, When injected at call start, Then all 10+ variables available in prompts
- **AC-FR031-001**: Given system prompt with tool instructions, When agent processes message, Then uses tools appropriately

**Independent Test**: Make test call, verify server tools invoked and webhooks triggered
**Dependencies**: Backend API deployed, ElevenLabs account access
**CRITICAL**: This is a BLOCKER for all other voice functionality - US-1 through US-15 depend on this configuration

---

### US-17: Knowledge Base Setup (Priority: P3 - Nice-to-Have)
```
Character documents uploaded → RAG enabled → Nikita has deep character knowledge
```
**Acceptance Criteria**:
- **AC-FR032-001**: Given backstory document uploaded, When agent queries knowledge base, Then character facts available
- **AC-FR032-002**: Given chapter behaviors document, When different chapter user calls, Then chapter-specific behaviors referenced
- **AC-FR032-003**: Given vice categories document, When personalization needed, Then vice descriptions available

**Independent Test**: Ask Nikita about her background, verify knowledge base provides consistent answers
**Dependencies**: US-16

---

### US-18: Fast Pre-Call Response (Priority: P0 - BLOCKER, Added Jan 2026)
```
Pre-call webhook → fetch cached prompt from PostgreSQL → return in <100ms → call connects instantly
```
**Acceptance Criteria**:
- **AC-FR033-001**: Given pre-call webhook received, When processing starts, Then NO LLM calls made (MetaPromptService not invoked)
- **AC-FR033-002**: Given pre-call webhook received, When processing starts, Then NO Neo4j calls made (NikitaMemory not invoked)
- **AC-FR033-003**: Given pre-call webhook received, When response returned, Then total latency <100ms
- **AC-FR034-001**: Given user with cached prompt, When pre-call received, Then `user.cached_voice_prompt` value used in response
- **AC-FR034-002**: Given user without cached prompt (first call), When pre-call received, Then static fallback prompt used

**Independent Test**: Time pre-call webhook with Supabase logs, verify <100ms response time with no LLM/Neo4j calls
**Dependencies**: US-10 (Post-Call Processing must cache prompt after call)
**CRITICAL**: This user story fixes the 90% call failure rate caused by real-time prompt generation

---

### US-10 (AMENDED): Post-Call Processing (Priority: P2 - Important)
```
Voice transcript → post_call_transcription webhook → 9-stage pipeline → memory enriched → prompt cached for next call
```
**Acceptance Criteria** (existing + new):
- **AC-FR015-001**: Given call ends, When post_call_transcription webhook received, Then transcript stored in conversations
- **AC-FR015-002**: Given transcript stored, When post-processing triggered, Then fact extraction runs on voice content
- **AC-FR015-003**: Given voice conversation, When thread detection runs, Then unresolved topics identified
- **AC-FR015-004**: Given voice call, When thought simulation runs, Then Nikita thoughts generated for call
- **AC-FR015-005**: Given webhook received, When HMAC signature validated, Then only ElevenLabs accepted
- **AC-FR015-006 (NEW)**: Given post-processing completes, When MetaPromptService generates prompt, Then stored in `user.cached_voice_prompt`
- **AC-FR015-007 (NEW)**: Given prompt cached, When next pre-call webhook received, Then cached prompt available in <10ms (database fetch only)

**Independent Test**: Complete voice call, verify `cached_voice_prompt` field populated in users table after post-processing
**Dependencies**: US-4, Post-Processing Pipeline (Spec 002)
**AMENDED Jan 2026**: Added AC-FR015-006 and AC-FR015-007 for prompt caching

---

## Intelligence Evidence

### Findings (Updated Dec 2025 - ElevenLabs SDK Research)

**ElevenLabs Conversational AI 2.0 Capabilities** (verified via MCP documentation):
- **Server Tools**: REST endpoints called by ElevenLabs agent with <2s timeout requirement
- **Dynamic Variables**: `{{var}}` injection with `system__` (auto) and `secret__` (hidden) prefixes
- **Overrides**: Full `conversation_config_override` at call start (prompt, voice, LLM, TTS)
- **Twilio Native**: Import phone number in ElevenLabs dashboard, agent handles inbound/outbound
- **Knowledge Base**: RAG with 20MB/300k char limit (supplemental context)
- **Webhooks**: `post_call_transcription` with HMAC-SHA256 verification

**Text Agent Patterns Replicable for Voice** (verified via code analysis):
- MetaPromptService: 19 context dimensions, 42 template variables → same for voice via dynamic variables
- NikitaDeps: Dependency injection pattern → VoiceAgentDeps equivalent
- Scoring: ScoreAnalyzer + ScoreCalculator → aggregate per-call for voice
- NikitaMemory: Graphiti interface → same client, server tool wrapper

**ElevenLabs Configuration** (confirmed):
- Agent ID: `agent_5801kdr3xza0fxfr2q3hdgbjrh9y`
- Twilio Phone: +41787950009
- Webhook URL: `https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/webhook`
- Server Tool URL: `https://nikita-api-1040094048579.us-central1.run.app/api/v1/voice/server-tool`

### Assumptions
- ASSUMPTION: ElevenLabs Conversational AI 2.0 handles STT/TTS ✅ VERIFIED
- ASSUMPTION: Server tools via REST endpoints with JSON response ✅ VERIFIED
- ASSUMPTION: Supabase stores transcripts (pgVector for semantic search) ✅ VERIFIED
- ASSUMPTION: Twilio native integration available in ElevenLabs ✅ VERIFIED

---

## Scope

### In-Scope
- Voice call initiation and management
- Real-time speech processing (via external service)
- Natural voice response generation
- Call scoring integration
- Transcript persistence
- Cross-modality memory sharing

### Out-of-Scope
- Video calls (voice only)
- Voice messages (asynchronous voice)
- Voice customization (pitch, speed user controls)
- Multi-party calls

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | Conversation storage, user context | ConversationRepository.create(platform='voice'), UserRepository.get() |
| 010-api-infrastructure | Voice callbacks | POST /api/v1/voice/server-tool, POST /api/v1/voice/webhook |
| 011-background-tasks | Scheduled event delivery | ScheduledEventRepository.create(), /tasks/deliver |

**Database Tables Used**:
- `users` (context loading: chapter, score, last_interaction_at)
- `user_metrics` (scoring context)
- `conversations` (platform='voice', transcript storage, elevenlabs_session_id)
- `score_history` (voice conversation scoring events)
- `scheduled_events` (cross-platform event scheduling for text/voice) **NEW**

**API Endpoints Required**:
- `POST /api/v1/voice/server-tool` - ElevenLabs server-side tools (get_context, get_memory, score_turn, update_memory)
- `POST /api/v1/voice/webhook` - ElevenLabs post-call webhooks (post_call_transcription, post_call_audio)

**Background Tasks** (via Spec 011):
- `/tasks/deliver` - Delivers scheduled voice reminders and cross-platform events
- Voice transcript post-processing enters existing 9-stage pipeline via `/tasks/process-conversations`

---

## Data Model

### Voice-Specific Columns (conversations table)

This spec defines the following columns on the `conversations` table (base table defined in 009-database-infrastructure):

| Column | Type | Description |
|--------|------|-------------|
| `elevenlabs_session_id` | TEXT (nullable) | ElevenLabs conversation session ID for resume/tracking |
| `transcript_raw` | TEXT (nullable) | Raw voice transcript with speaker attribution |

**Usage**:
- `elevenlabs_session_id`: Set when voice call starts, used for resuming interrupted calls and analytics
- `transcript_raw`: Full conversation transcript stored for memory integration (Graphiti) and user review

**Reference**: See `nikita/db/models/conversation.py` lines 78-79

---

## Risks & Mitigations

### Risk 1: Latency Destroys Immersion
**Description**: Response latency makes conversation feel unnatural
**Likelihood**: Medium (0.5) | **Impact**: High (8) | **Score**: 4.0
**Mitigation**: Target <500ms, use filler phrases, optimize pipeline

### Risk 2: Voice Quality Issues
**Description**: Robotic or artifact-laden voice breaks immersion
**Likelihood**: Low (0.3) | **Impact**: High (8) | **Score**: 2.4
**Mitigation**: Use premium voice service, test extensively, fallback options

### Risk 3: Cost Escalation
**Description**: Voice processing costs scale unexpectedly
**Likelihood**: Medium (0.5) | **Impact**: Medium (5) | **Score**: 2.5
**Mitigation**: Monitor usage, implement call time limits, optimize routing

---

## Success Metrics

- Call completion rate: 90%+ calls complete without technical issues
- Latency performance: 80%+ responses < 500ms
- User satisfaction: Voice calls rated more engaging than text-only
- Return rate: Users who make calls return more frequently

---

**Version**: 4.0
**Last Updated**: 2026-01-10
**Changes in v4.0** (2026-01-10):
- **CRITICAL ARCHITECTURE FIX**: "Compute-after, serve-fast" pattern for pre-call webhook
- **FR-033 (NEW)**: Pre-Call Webhook Performance - MUST respond in <100ms, NO LLM/Neo4j calls
- **FR-034 (NEW)**: Cached Voice Prompt Field - `users.cached_voice_prompt` for fast retrieval
- **FR-015 (AMENDED)**: Post-Call Processing now caches prompt for NEXT call
- **FR-028 (AMENDED)**: Pre-call webhook fetches cached prompt (no real-time generation)
- **US-18 (NEW)**: Fast Pre-Call Response (P0 BLOCKER) - fixes 90% call failure rate
- **US-10 (AMENDED)**: Added AC-FR015-006 and AC-FR015-007 for prompt caching
- Root cause: Pre-call was calling LLM + Neo4j causing 5-30+ second delays

**Changes in v3.0** (2026-01-03):
- Added ElevenLabs Dashboard Configuration Requirements section (FR-027 to FR-032)
- Added US-16: ElevenLabs Dashboard Configuration (P0 BLOCKER)
- Added US-17: Knowledge Base Setup (P3 Nice-to-Have)
- FR-027: Server Tools Dashboard Configuration
- FR-028: Conversation Initiation Client Data Webhook (pre-call webhook)
- FR-029 to FR-032: Additional dashboard configuration requirements

**Changes in v2.0** (2025-12-30):
- Added FR-016 to FR-026 (11 new functional requirements)
- Added US-11 to US-15 (5 new user stories)
- Updated Intelligence Evidence with ElevenLabs SDK research findings
- Added ElevenLabs configuration details (agent ID, webhook URLs)
- Updated assumptions with verification status
