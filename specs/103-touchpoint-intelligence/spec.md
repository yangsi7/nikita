# Spec 103: Touchpoint Intelligence

## Overview

Enriches the proactive touchpoint system with 5 intelligence sources: life events wired to message generation, PsycheState integration into strategic silence, content deduplication, conversation thread injection, and vice category loading.

## Scope

| ID | Issue | Type | Severity |
|----|-------|------|----------|
| G7/I2 | Life events not wired to MessageGenerator | Gap | HIGH |
| G8/I3 | PsycheState not loaded into StrategicSilence | Gap | HIGH |
| G9 | No touchpoint content deduplication | Gap | MEDIUM |
| I1 | Open conversation_threads not injected into touchpoint prompt | Improvement | MEDIUM |
| I4 | Vice categories not loaded into touchpoint generation | Improvement | MEDIUM |

## Functional Requirements

### FR-001: Wire Life Events to MessageGenerator (G7/I2)

**Problem**: `TouchpointEngine._generate_message()` calls `generator.generate()` but doesn't pass `life_event_description` even though `evaluate_and_schedule_for_user()` receives `life_events` and the generator already accepts the parameter.

**Solution**: Thread life event description from scheduling through to message generation. Store event description in touchpoint trigger_context, read it during generation.

**Files**: `nikita/touchpoints/engine.py`

**AC**:
- AC-1.1: `evaluate_and_schedule_for_user()` stores first life event description in `trigger_context` metadata
- AC-1.2: `_generate_message()` extracts life event from touchpoint trigger_context and passes to `generator.generate(life_event_description=...)`
- AC-1.3: When no life events, behavior unchanged (None passed)

### FR-002: PsycheState Integration into StrategicSilence (G8/I3)

**Problem**: `StrategicSilence.apply_strategic_silence()` only sees emotional_state (valence/arousal/dominance). PsycheState has `defense_mode` and `attachment_activation` which should inform silence decisions.

**Solution**: Load PsycheState for user, inject defense_mode and attachment_activation into silence evaluation. Guarded/withdrawing defense → increase silence. Avoidant attachment → increase silence.

**Files**: `nikita/touchpoints/engine.py`, `nikita/touchpoints/silence.py`

**AC**:
- AC-2.1: `TouchpointEngine._evaluate_silence()` loads PsycheState for user via `PsycheStateRepository`
- AC-2.2: `StrategicSilence.apply_strategic_silence()` accepts optional `psyche_state: dict` parameter
- AC-2.3: `defense_mode == "withdrawing"` adds +0.5 to emotional modifier
- AC-2.4: `defense_mode == "guarded"` adds +0.3 to emotional modifier
- AC-2.5: `attachment_activation == "avoidant"` adds +0.3 to emotional modifier
- AC-2.6: Graceful degradation: if PsycheState not available, behavior unchanged

### FR-003: Touchpoint Content Deduplication (G9)

**Problem**: No check if a recently sent touchpoint had similar content. Nikita could send "thinking about you..." twice in a row.

**Solution**: Track hash of last 5 delivered touchpoint messages per user. Before delivering, check if new message content is similar to any recent hash.

**Files**: `nikita/touchpoints/engine.py`, `nikita/touchpoints/store.py`

**AC**:
- AC-3.1: `TouchpointStore.get_recent_delivered_content()` returns last 5 delivered message contents for user
- AC-3.2: Before delivery, check if new message has >70% similarity (SequenceMatcher) with any recent message
- AC-3.3: If similar, regenerate message (one retry) or skip with reason "content_dedup"
- AC-3.4: Similarity check is O(N) where N=5, no performance concern

### FR-004: Inject Conversation Threads into Touchpoint Prompt (I1)

**Problem**: Open conversation_threads (follow-ups, questions, promises) are not used in touchpoint generation. Nikita could proactively reference unresolved topics.

**Solution**: Load open threads via ConversationThreadRepository, format and inject into MessageGenerator prompt context.

**Files**: `nikita/touchpoints/engine.py`, `nikita/touchpoints/generator.py`

**AC**:
- AC-4.1: `MessageGenerator.generate()` accepts optional `open_threads: list[dict]` parameter
- AC-4.2: Open threads formatted as bullet list in template: "Open topics: - [follow_up] content..."
- AC-4.3: Max 3 threads injected (highest priority: questions > promises > follow_ups > topics)
- AC-4.4: `TouchpointEngine._generate_message()` loads threads and passes to generator

### FR-005: Vice Categories in Touchpoint Generation (I4)

**Problem**: Touchpoint messages don't reflect user's vice preferences. Nikita's proactive messages could subtly reference known vices.

**Solution**: Load top 2 vice categories via VicePreferenceRepository, inject into MessageGenerator prompt.

**Files**: `nikita/touchpoints/engine.py`, `nikita/touchpoints/generator.py`

**AC**:
- AC-5.1: `MessageGenerator.generate()` accepts optional `vice_hints: list[str]` parameter
- AC-5.2: Vice hints formatted as: "Personality hints: she knows you enjoy [category1] and [category2]"
- AC-5.3: Only top 2 vices with `engagement_score > 0.3` included
- AC-5.4: `TouchpointEngine._generate_message()` loads vices and passes to generator

## Non-Functional Requirements

- All enrichments are additive — existing touchpoint behavior unchanged when data unavailable
- Graceful degradation for every new data source (psyche, threads, vices)
- No additional DB round-trips during delivery (load all during scheduling/generation)
- Content dedup check must be <10ms

## Dependencies

- PsycheState system (Spec 056) — already implemented
- ConversationThread system (Spec 012) — already implemented
- Vice system (Spec 037) — already implemented

## Test Strategy

- Unit tests for each FR with mocked DB calls
- Test graceful degradation when data sources unavailable
- Test content dedup similarity threshold
- Test thread/vice injection formatting
