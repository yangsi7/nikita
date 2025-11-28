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

## Intelligence Evidence

### Findings
- User stated: "ElevenLabs Agent SDK handles all the complex voice stuff"
- User stated: "Gives the agent ability to call tools, APIs server side, client side"
- nikita/config/elevenlabs.py - Agent ID abstraction mentioned in CLAUDE.md
- memory/architecture.md - Voice agent architecture planned

### Assumptions
- ASSUMPTION: ElevenLabs Conversational AI 2.0 handles STT/TTS
- ASSUMPTION: Server tools via ElevenLabs webhooks
- ASSUMPTION: Supabase stores transcripts (pgVector for semantic search)

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
| 010-api-infrastructure | Voice callbacks | POST /api/v1/voice/server-tool, POST /api/v1/voice/callback |

**Database Tables Used**:
- `users` (context loading: chapter, score, last_interaction_at)
- `user_metrics` (scoring context)
- `conversations` (platform='voice', transcript storage, elevenlabs_session_id)
- `score_history` (voice conversation scoring events)

**API Endpoints Required**:
- `POST /api/v1/voice/server-tool` - ElevenLabs server-side tools (get_context, score_turn)
- `POST /api/v1/voice/callback` - Conversation event logging

**No Background Tasks** - Voice is real-time synchronous

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

**Version**: 1.0
**Last Updated**: 2025-11-28
