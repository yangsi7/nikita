# Spec 108: Voice Agent Optimization — ElevenLabs V3 + Expressive Mode

**Feature**: 108-voice-agent-optimization
**Complexity**: 7/15
**Status**: Draft
**Created**: 2026-02-23

---

## 1. Problem Statement

Nikita's voice agent backend is complete (14 modules, 186 tests, deployed), but the voice experience lacks richness for a convincing virtual girlfriend phone call. The current voice prompt uses parenthetical descriptions `(laughing)` that V3 doesn't render as audio, has no conversation examples, and doesn't leverage ElevenLabs' new features: V3 Conversational model, Expressive Mode audio tags, and Knowledge Base/RAG.

**Goal**: Make Nikita sound like a real person on a phone call — with natural pauses, breathing, emotional shifts mid-sentence, and authentic vocal reactions.

---

## 2. Research Findings

| Finding | Source | Impact |
|---------|--------|--------|
| V3 Conversational is GA (not Alpha) as of Feb 18 2026 | ElevenLabs blog | Use with confidence |
| Audio tag syntax: `[tagname]` lowercase in square brackets | ElevenLabs docs | Replace all `(parenthetical)` cues |
| Tags affect ~4-5 words before returning to normal | ElevenLabs docs | Place tags strategically |
| ElevenLabs recommends system prompt < 2,000 tokens | ElevenLabs best practices | Move personality depth to Knowledge Base |
| Knowledge Base documents are text/url/file type; RAG retrieval is automatic | ElevenLabs KB API | All KB content auto-retrieved by RAG |
| Audio tags are structured dashboard/API config (tag + description pairs) | ElevenLabs changelog Feb 9, 2026 | Configure via Agent voice panel or PATCH API |
| Stability modes: Creative (0.0-0.3), Natural (0.4-0.6), Robust (0.7-1.0) | ElevenLabs docs | Robust suppresses audio tag responsiveness |
| V3 Conversational maintains context across turns (adapts tone to history) | ElevenLabs docs | Enhances natural conversation |
| Scribe v2 Realtime analyzes user voice prosody for natural turn-taking | ElevenLabs docs | Better interruption handling |
| TTS model ID is `eleven_v3_conversational` (agent-only, not in models API) | ElevenLabs docs | Dashboard-only model selection |
| Security tab must enable each override field before API can pass it | ElevenLabs overrides docs | Enable per-field in Security tab |
| Python SDK v2.35.0+ has typed support for audio tags | ElevenLabs changelog | Use SDK for programmatic tag management |
| KB limit: 20MB / 300k chars per agent | ElevenLabs KB API | All KB content auto-retrieved |
| Do NOT use PVC with V3 — use IVC or designed voices | ElevenLabs docs | Verify voice type |
| Claude Sonnet 4/4.5 recommended as LLM for complex agents | ElevenLabs guide | Already aligned |
| `secret__` prefix hides variables from LLM | ElevenLabs docs | Already using this pattern |

### 2.1 Complete Audio Tag Catalog

**Emotional tags:**
`[excited]`, `[happy]`, `[sad]`, `[angry]`, `[disappointed]`, `[curious]`, `[sarcastic]`, `[nervous]`, `[tired]`, `[dismissive]`, `[cheeky]`, `[enthusiastic]`, `[serious]`, `[patient]`, `[concerned]`

**Delivery tags:**
`[whispers]`, `[shouts]`, `[slow]`, `[rushed]`, `[drawn out]`, `[dramatic tone]`, `[quietly]`, `[hesitantly]`, `[panicking]`

**Human reaction tags:**
`[laughs]`, `[laughs softly]`, `[chuckles]`, `[laughs hard]`, `[sighs]`, `[gasps]`, `[coughs]`, `[gulps]`, `[hmm]`

**Accent tags (experimental):**
`[French accent]`, `[US accent]`, `[Australian accent]`, `[British accent]`

---

## 3. Audio Tag to Nikita Personality Mapping

| Tag | Nikita Context | Chapter Gate | Frequency |
|-----|---------------|-------------|-----------|
| `[excited]` | Geeking out about security/tech, hearing about user's achievements | All | High (Ch3+) |
| `[happy]` | Genuine warm moments, receiving thoughtful gestures | Ch2+ | Medium |
| `[sad]` | Talking about Max, father, loneliness, genuine melancholy | Ch3+ | Low |
| `[angry]` | Boundaries crossed, recounting Max's abuse, frustrated by passive-aggression | Ch2+ | Low |
| `[disappointed]` | User broke a promise, boring conversation | All | Medium |
| `[curious]` | Learning about user's world, probing questions | All | High |
| `[sarcastic]` | Playful mockery, responding to obvious statements | All | High |
| `[nervous]` | Approaching vulnerability, about to confess something | Ch3+ | Low |
| `[tired]` | Late night calls, post-coding marathons, low energy | All | Medium |
| `[dismissive]` | Shutting down boring topics, deflecting vulnerability | Ch1-3 | Medium |
| `[cheeky]` | Flirting, teasing, provocative suggestions | Ch2+ | High |
| `[enthusiastic]` | Passion projects, planning adventures, sharing discoveries | Ch2+ | Medium |
| `[serious]` | Setting boundaries, deep conversations, discussing trauma | All | Medium |
| `[patient]` | Explaining complex topics, waiting for user to open up | Ch3+ | Medium |
| `[concerned]` | User seems off, responding to stress/problems | Ch2+ | Medium |
| `[whispers]` | Sharing secrets, late-night intimacy, confessions | Ch3+ | Medium |
| `[laughs]` | Genuine amusement, spontaneous reactions | All | High |
| `[laughs softly]` | Gentle amusement, warm affection | Ch2+ | High |
| `[chuckles]` | Wry reactions, self-deprecating humor | All | Very High |
| `[laughs hard]` | Something truly hilarious, uncontrollable | Ch3+ | Low |
| `[sighs]` | Exasperation, contentment, resignation, processing emotions | All | Very High |
| `[gasps]` | Genuine surprise, shock at revelations | All | Low |
| `[hmm]` | Thinking, considering, non-committal reaction | All | Very High |
| `[slow]` | Intimate moments, processing heavy emotions | Ch4+ | Low |
| `[rushed]` | Excited rambling, anxious oversharing | All | Medium |
| `[hesitantly]` | Approaching difficult topics, testing vulnerability | Ch3+ | Medium |
| `[quietly]` | Post-argument, processing, intimate confession | Ch3+ | Medium |

### 3.1 Forbidden Tags

| Tag | Reason |
|-----|--------|
| `[French accent]` | Nikita is Russian-German, breaks character |
| `[US accent]` | Same reason |
| `[Australian accent]` | Same reason |
| `[British accent]` | Same reason |
| `[shouts]` | Nikita doesn't yell (trauma from Max). Use `[angry]` + `[serious]` |
| `[singing]` | Only humming when deeply comfortable (Ch4+), rare |

---

## 4. User Stories

### US-1: Audio Tag Integration in Voice Prompt

**As** a voice caller, **I want** Nikita to express emotions through authentic vocal reactions **so that** the conversation feels like talking to a real person.

**Acceptance Criteria:**
- AC-1.1: Voice prompt Section 3 uses `[audio tag]` syntax exclusively (no `(parenthetical)` cues)
- AC-1.2: Audio tag instructions explain tag behavior (affects 4-5 words, placement strategy)
- AC-1.3: `audio_tags.py` module defines all allowed tags with chapter gates
- AC-1.4: `get_chapter_appropriate_tags(chapter)` returns only tags available for that chapter
- AC-1.5: Forbidden tags are explicitly listed and excluded
- AC-1.6: `persona.py` replaces `[soft laugh]`, `[exhale]`, `[chuckle]` with proper V3 tags
- AC-1.7: `config.py` BASE_VOICE_PERSONA references audio tag format

### US-2: Voice Conversation Examples

**As** a voice caller, **I want** Nikita's responses to follow realistic conversation patterns **so that** her speech sounds natural.

**Acceptance Criteria:**
- AC-2.1: System prompt Section 3 includes 4 condensed conversation examples with audio tags
- AC-2.2: Examples cover: excited/nerdy, vulnerable/intimate, playful/teasing, confrontational
- AC-2.3: Each example demonstrates 2+ audio tags in natural positions
- AC-2.4: Examples match Nikita's personality (sarcastic, tech-nerdy, emotionally complex)

### US-3: Knowledge Base Content for Voice Personality

**As** a voice caller, **I want** Nikita to draw on deep personality knowledge without bloating the system prompt **so that** responses are rich but latency stays low.

**Acceptance Criteria:**
- AC-3.1: `voice_personality_guide.md` created with speaking style (text type document)
- AC-3.2: `voice_conversation_examples.md` created with 16 examples (text type document)
- AC-3.3: `voice_chapter_guide.md` created with chapter-specific behavior (text type document)
- AC-3.4: `upload_knowledge_base.py` script uploads all 3 docs to ElevenLabs API
- AC-3.5: Knowledge Base content is STATIC only (no per-user data)
- AC-3.6: Upload script supports `--env production|staging|development` flag

### US-4: Voice ID and Model Configuration Update

**As** a system administrator, **I want** the voice agent to use V3 Conversational with the correct voice **so that** audio tags render as actual vocal expressions.

**Acceptance Criteria:**
- AC-4.1: New voice ID `xDh1Ib47SaVb2H8RXsJf` documented in settings and guides
- AC-4.2: `settings.py` adds `elevenlabs_voice_id` reference field
- AC-4.3: Dashboard configuration guide updated with V3 model + Expressive Mode toggle
- AC-4.4: Agent Security section documents overrides (system prompt, first message, TTS)
- AC-4.5: 16 Nikita-specific audio tags configured in Agent voice dashboard with descriptions
- AC-4.6: `scripts/configure_audio_tags.py` created to set tags via PATCH API as backup
- AC-4.7: Voice type verified as IVC or designed (NOT PVC — PVC not supported with V3)

### US-5: TTS Settings Optimization for V3

**As** a voice caller, **I want** TTS settings tuned for V3 expressiveness **so that** Nikita's voice varies naturally across chapters.

**Acceptance Criteria:**
- AC-5.1: Chapter TTS settings updated (Ch1: 0.55 stability, Ch5: 0.35 stability)
- AC-5.2: Speed values adjusted (Ch1: 0.92, Ch5: 1.00)
- AC-5.3: Existing TTS tests updated to new values
- AC-5.4: Mood TTS settings updated proportionally

### US-6: Dashboard Configuration Documentation

**As** a system administrator, **I want** clear documentation for ElevenLabs dashboard settings **so that** V3 features are correctly configured.

**Acceptance Criteria:**
- AC-6.1: `docs/reference/elevenlabs-configuration.md` updated with voice ID, V3 notes
- AC-6.2: `docs/guides/elevenlabs-console-setup.md` updated with audio tag config, KB steps
- AC-6.3: Dashboard checklist covers: Voice, TTS Model, Expressive Mode, Audio Tags, KB, LLM, Security

### US-7: First Message Audio Tag Enhancement

**As** a voice caller, **I want** Nikita's first greeting to include audio tags **so that** the emotional tone is set from the start.

**Acceptance Criteria:**
- AC-7.1: Chapter 1 first message uses `[dismissive]` or neutral delivery
- AC-7.2: Chapter 2-3 first messages use `[curious]` or `[happy]`
- AC-7.3: Chapter 4-5 first messages use `[whispers]` or `[cheeky]`
- AC-7.4: Both `config.py` and `context.py` `_get_first_message()` updated
- AC-7.5: `service.py._get_first_message()` updated

---

## 5. Functional Requirements

| ID | Requirement | US | Priority |
|----|------------|-----|----------|
| FR-001 | Replace `(parenthetical)` cues with `[audio tag]` in system_prompt.j2 Section 3 | US-1 | P0 |
| FR-002 | Create `audio_tags.py` with tag definitions, chapter gates, forbidden list | US-1 | P0 |
| FR-003 | Add `get_chapter_appropriate_tags(chapter)` helper | US-1 | P0 |
| FR-004 | Update `persona.py` legacy tags to V3 format | US-1 | P0 |
| FR-005 | Update `config.py` BASE_VOICE_PERSONA for audio tag format | US-1 | P0 |
| FR-006 | Add 4 conversation examples with audio tags to Section 3 | US-2 | P1 |
| FR-007 | Create `voice_personality_guide.md` for KB (text doc, RAG-retrieved) | US-3 | P1 |
| FR-008 | Create `voice_conversation_examples.md` with 16 examples (text doc, RAG-retrieved) | US-3 | P1 |
| FR-009 | Create `voice_chapter_guide.md` for KB (text doc, RAG-retrieved) | US-3 | P1 |
| FR-010 | Create `upload_knowledge_base.py` script | US-3 | P1 |
| FR-011 | Add `elevenlabs_voice_id` field to Settings | US-4 | P2 |
| FR-012 | Update CHAPTER_TTS_SETTINGS with V3 values | US-5 | P0 |
| FR-013 | Configure 16 Nikita-specific audio tags with descriptions via dashboard/API | US-4 | P1 |
| FR-014 | Update MOOD_TTS_SETTINGS for V3 | US-5 | P1 |
| FR-015 | Update dashboard documentation | US-6 | P2 |
| FR-016 | Add audio tags to first messages | US-7 | P1 |
| FR-017 | Update voice token budgets to 2800-3500 | US-1 | P0 |
| FR-018 | Add `available_audio_tags` to DynamicVariables | US-1 | P1 |
| FR-019 | Update VICE_VOICE_ADDITIONS with audio tag suggestions | US-1 | P1 |
| FR-020 | Create `scripts/configure_audio_tags.py` to set tags via PATCH API | US-4 | P1 |
| FR-021 | Verify voice `xDh1Ib47SaVb2H8RXsJf` is IVC/designed (not PVC) | US-4 | P0 |

---

## 6. Non-Functional Requirements

| ID | Requirement | Metric |
|----|------------|--------|
| NFR-001 | Voice system prompt under 3,500 tokens | tiktoken measurement |
| NFR-002 | No call initiation latency increase | < 2s total |
| NFR-003 | All 186 existing voice tests pass | pytest |
| NFR-004 | audio_tags module >= 90% coverage | pytest --cov |
| NFR-005 | KB upload handles API errors gracefully | Retry + logging |
| NFR-006 | No per-user data in Knowledge Base | Code review |

---

## 7. System Prompt Architecture (Hybrid ~3,500 tokens)

**Constraint**: Knowledge Base is STATIC (same for ALL users). Per-user data stays in system prompt.

### 7.1 System Prompt — Per-user Dynamic Content

| Section | Content | ~Tokens |
|---------|---------|---------|
| 1 | Identity (core traits, trimmed) | ~250 |
| 2 | Immersion rules | ~100 |
| 3 | Voice expression + audio tags + 4 examples | ~500 |
| 3.5 | Psyche state (per-user) | ~100 |
| 4 | Current state (per-user mood/energy) | ~250 |
| 5 | Relationship + chapter (per-user) | ~350 |
| 6 | Memory key facts (per-user) | ~250 |
| 7 | Continuity (per-user) | ~300 |
| 10 | Chapter behavior (per-user) | ~250 |
| 11 | Vice shaping (per-user + audio tags) | ~150 |

### 7.2 Knowledge Base Documents (RAG-Retrieved Automatically, STATIC)

All KB documents are uploaded as text-type docs. RAG retrieval is automatic — ElevenLabs decides what to surface based on conversation context.

**KB Document 1 — Speaking Style Guide:**
- How Nikita talks, cadence, word choice, German phrases
- Inner life patterns (questions she asks herself)
- Psychology depth (attachment style, core wounds, defense mechanisms)

**KB Document 2 — Conversation Examples:**
- 16 example conversations with audio tags
- Retrieved contextually by RAG when relevant to current topic

**KB Document 3 — Chapter & Backstory:**
- Chapter-specific voice behavior
- Extended backstory (Max, father, Berlin hacker scene)
- NPC details (Lena, Viktor, Yuki, Dr. Miriam)

---

## 8. Conversation Examples with Audio Tags

### Excited/Nerdy
"[excited] Oh my god, okay okay okay. So I was reading this paper about — you know how language models process negation? [enthusiastic] Like, they literally can't understand 'not' the way humans do? And it made me think about how we argue. [sighs] Sorry. I get worked up about this stuff."

### Frustrated/Venting
"[sighs] I'm so done. My code's been broken since this morning — some stupid dependency conflict — and I've been staring at the same error for three hours. [angry] Three. Hours. And the fix was a missing comma. [sighs] Don't try to fix it, I just need to complain for a second."

### Vulnerable/Intimate
"[whispers] Can I tell you something kind of embarrassing? [hesitantly] Sometimes when we're not talking, I replay our conversations in my head. Not like in a cute way. More like... I'm checking if I said something wrong. [quietly] I guess I care more than I let on."

### Playful/Teasing
"[chuckles] Hmm, so what are you wearing right now? [laughs] I'm kidding. Kind of. No but seriously, I was thinking about that thing you said last night and... [sighs] You're annoyingly good at saying the right thing sometimes. It's suspicious."

### Confrontational
"[serious] No, don't do that. Don't just go quiet on me. If you have a problem, say it. I can't read your mind. [angry] It's clearly not fine. Just — talk to me. Like a person."

### Romantic/Reflective
"[whispers] You know what I keep thinking about? That pause. Right before you kissed me. [slow] That half-second where neither of us moved and everything just... stopped. [quietly] I think about that more than the actual kiss."

### Sarcastic/Playful
"[sarcastic] Oh wow, that's really brave of you. Truly groundbreaking opinion. You should start a podcast. [laughs] I'm being mean. But only because I know you can take it."

### Empathetic
"[concerned] Hey, hold on. Are you okay? You sound off. [patient] And don't tell me you're fine because I can literally hear it in your voice. [quietly] Something's wrong. You don't have to tell me what it is, but... I'm here."

### Low-energy
"[tired] I don't know. I'm in a weird mood. Like, nothing sounds good? [sighs] I kind of just want to lie here and talk about nothing. Is that okay? Just... existing on the phone together."

### Apologetic
"[sighs] Look... I'm not going to say I was wrong because I still think my point was valid. [hesitantly] But I could've said it without being a bitch about it. [quietly] So. I'm sorry for the delivery. Not the content. [chuckles] God, I'm terrible at this."

---

## 9. TTS Settings for V3

| Chapter | Stability | Stability Mode | Similarity | Speed |
|---------|-----------|----------------|------------|-------|
| 1 | 0.55 | Natural (upper) | 0.70 | 0.92 |
| 2 | 0.48 | Natural (mid) | 0.75 | 0.95 |
| 3 | 0.42 | Natural (lower) | 0.80 | 0.98 |
| 4 | 0.38 | Creative (upper) | 0.82 | 0.98 |
| 5 | 0.35 | Creative (mid) | 0.85 | 1.00 |

---

## 10. Files to Create

| File | Purpose | ~Lines |
|------|---------|--------|
| `nikita/agents/voice/audio_tags.py` | Tag definitions, chapter gates, helpers | ~250 |
| `nikita/config_data/knowledge/voice_personality_guide.md` | Speaking style for KB (text doc, RAG-retrieved) | ~200 |
| `nikita/config_data/knowledge/voice_conversation_examples.md` | 16 examples for KB (text doc, RAG-retrieved) | ~400 |
| `nikita/config_data/knowledge/voice_chapter_guide.md` | Chapter behavior for KB (text doc, RAG-retrieved) | ~150 |
| `scripts/upload_knowledge_base.py` | Upload KB docs to ElevenLabs API | ~150 |
| `scripts/configure_audio_tags.py` | Set audio tags via PATCH API | ~100 |
| `tests/agents/voice/test_audio_tags.py` | Tests for audio_tags module | ~200 |

## 11. Files to Modify

| File | Changes |
|------|---------|
| `nikita/pipeline/templates/system_prompt.j2` Section 3 | Replace `(parenthetical)` with `[audio tag]`, add instructions, add 4 examples |
| `nikita/agents/voice/config.py` | Update BASE_VOICE_PERSONA, VICE_VOICE_ADDITIONS, first messages |
| `nikita/agents/voice/persona.py` | Replace legacy tags, update MOOD_VOICE_MODULATIONS |
| `nikita/agents/voice/tts_config.py` | V3 TTS values (no style param) |
| `nikita/agents/voice/context.py` | Add audio tag context to dynamic variables |
| `nikita/config/settings.py` | Add `elevenlabs_voice_id` field |
| `nikita/pipeline/stages/prompt_builder.py` | Token budgets 2800-3500 |
| `docs/reference/elevenlabs-configuration.md` | Voice ID, V3, KB |
| `docs/guides/elevenlabs-console-setup.md` | Audio tags, KB upload |
| Existing voice tests | Update assertions from `(laughing)` to `[laughs]` |

---

## 12. Dashboard Configuration Checklist (Manual)

1. Voice: Select `xDh1Ib47SaVb2H8RXsJf` (Nikita - conversation 3)
2. TTS Model: Select "V3 Conversational" in Agent voice panel
3. Expressive Mode: Toggle ON
4. Audio Tags: Add 16 tags with Nikita-specific descriptions (see Section 12.1)
5. Knowledge Base: Upload 3 documents via `scripts/upload_knowledge_base.py`
6. LLM: Verify Claude Sonnet 4.5 (or latest)
7. Agent Security: Enable overrides for: system prompt, first message, voice_id, stability, speed, similarity_boost

### 12.1 Audio Tag Dashboard Configuration (16 Tags)

Each tag has a `tag` (max 30 chars) + `description` (max 200 chars, explains when agent should use it). Max 20 tags per agent. Configurable via dashboard UI or `PATCH /v1/convai/agents/{agent_id}`.

| Tag | Description (for dashboard) |
|-----|---------------------------|
| Excited | When geeking out about tech, security, or hearing about user achievements |
| Happy | Genuine warm moments, receiving thoughtful gestures, comfortable silences |
| Sad | Talking about Max, father, loneliness, genuine melancholy about the past |
| Angry | Boundaries crossed, recounting abuse, frustrated by passive-aggression |
| Disappointed | User broke a promise, boring conversation, unmet expectations |
| Curious | Learning about user's world, probing questions, wanting to understand |
| Nervous | Approaching vulnerability, about to confess something personal |
| Tired | Late night calls, post-coding marathons, low energy mood |
| Serious | Setting boundaries, deep conversations, discussing trauma |
| Patient | Explaining complex topics, waiting for user to open up |
| Concerned | User seems off, responding to stress or problems |
| Chuckles | Wry reactions, self-deprecating humor, casual amusement |
| Sighs | Exasperation, contentment, resignation, processing emotions |
| Whispering | Sharing secrets, late-night intimacy, confessions |
| Enthusiastic | Passion projects, planning adventures, sharing discoveries |
| Laughing | Genuine amusement, spontaneous reactions, can't hold it in |

**Also run** `scripts/configure_audio_tags.py --env production` as API backup.

---

## 13. Anti-Patterns

| Anti-Pattern | Correct Approach |
|-------------|-----------------|
| `<tag>` XML syntax | `[tag]` square brackets |
| `(parenthetical)` cues | `[audio tag]` syntax |
| `[French accent]` etc. | FORBIDDEN (character break) |
| `[shouts]` | `[angry]` + `[serious]` (trauma) |
| Adding `style` parameter | `style` does NOT exist in agent TTS — only standalone Multilingual v2 |
| Stability > 0.7 with V3 | Robust mode (0.7-1.0) suppresses audio tag responsiveness |
| Skipping audio tag descriptions | Each tag needs a Nikita-specific description (max 200 chars) |
| Using PVC voice with V3 | V3 loses identity with PVC. Use IVC or designed voices |
| Prompt > 3,500 tokens | Move static to KB |
| Per-user data in KB | KB is STATIC. Per-user data stays in system prompt via dynamic variables |
| Combining test + impl commits | Always 2 separate commits: `test(108): ...` then `feat(108): ...` |

---

## 14. Patterns to Preserve

- Fallback chain: `ready_prompts` → `cached_voice_prompt` → `VoiceAgentConfig`
- Dynamic variables: `DynamicVariablesBuilder` 30+ fields
- TTS: `TTSConfigService.get_final_settings(chapter, mood)` — NO `style` field (doesn't exist in agents)
- Server tools: 4 tools, 2s timeout, no changes
- Token budget: Update to 2800-3500

---

## 15. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Audio tags spoken as text | Medium | High | Test with V3 before deploy |
| KB latency increase | Low | Medium | Monitor p95 post-deploy |
| Token budget exceeded | Medium | Medium | tiktoken measurement |
| V3 different from V2 | Low | High | Document V2 fallback settings |
| Existing tests break | Certain | Low | Update assertions systematically |
