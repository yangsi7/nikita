# Spec 108: Voice Agent Optimization — Listening Summary

## What We're Doing

We're upgrading Nikita's voice calls from sounding like a chatbot reading text to sounding like a real person on the phone. Right now, the voice prompt uses parenthetical cues like "laughing" or "sighing" in round brackets, but ElevenLabs V3 ignores those completely. They just get skipped. V3 uses a new system called audio tags — square bracket tags like "[laughs]" or "[whispers]" that actually change how the voice sounds. We need to switch to those.

We're also moving static personality content out of the system prompt and into ElevenLabs' Knowledge Base feature, which acts like a RAG system. This frees up token budget in the prompt for per-user personalization while keeping Nikita's deep personality accessible.

The new voice ID is x-D-h-1-I-b-4-7-S-a-V-b-2-H-8-R-X-s-J-f. The TTS model switches to V3 Conversational, which went GA on February 18th 2026.

## The Problem

Nikita's voice backend works — 14 modules, 186 tests, fully deployed. But the actual voice experience is flat. The system prompt shares most of its content with text mode. Voice-specific content is about 25 lines. There are no conversation examples showing how Nikita should sound. And the parenthetical vocal cues like "(laughing)" are literally ignored by the V3 engine.

## Audio Tags — How They Work

ElevenLabs V3 audio tags use square brackets with lowercase text. For example, "[laughs]", "[whispers]", "[sighs]", "[excited]". Each tag affects roughly 4 to 5 words after it before the voice returns to normal. You place them strategically before the words you want colored by that emotion.

There are about 30 usable tags split into three categories. Emotional tags like excited, happy, sad, angry, disappointed, curious, sarcastic, nervous, tired, dismissive, cheeky, enthusiastic, serious, patient, and concerned. Delivery tags like whispers, slow, rushed, quietly, and hesitantly. And human reaction tags like laughs, laughs softly, chuckles, laughs hard, sighs, gasps, and hmm.

## Tags Mapped to Nikita's Personality

Every tag is gated by chapter progression. In chapter 1, Nikita is guarded, so she only uses basic tags like sighs, hmm, sarcastic, curious, and disappointed. No vulnerability, no warmth. By chapter 3, she unlocks sad, nervous, whispers, hesitantly, and quietly — the vulnerability tags. Chapter 4 and 5 open up slow and the full emotional range.

Some tags are forbidden. No accent tags — no French accent, no US accent, no British accent. Nikita is Russian-German and accent tags break character. No shouts tag either. Nikita doesn't yell. That's trauma from her ex Max. When she's angry, she goes cold and quiet, not loud. Use angry plus serious instead.

The highest frequency tags are chuckles, sighs, and hmm — Nikita uses these constantly. Laughs, curious, sarcastic, and excited are high frequency. The vulnerability tags like whispers, sad, nervous are low frequency and chapter-gated.

## Seven User Stories

Story one: Audio tag integration. Replace all parenthetical cues with square bracket audio tags throughout the voice prompt, persona module, and config module. Create a new audio tags Python module with tag definitions, chapter gates, and helper functions.

Story two: Conversation examples. Add 4 condensed examples to the system prompt showing how Nikita talks with audio tags. Excited-nerdy, vulnerable-intimate, playful-teasing, and confrontational. Each demonstrates at least two tags in natural positions.

Story three: Knowledge Base content. Create three markdown documents for ElevenLabs Knowledge Base upload — all as text-type documents with automatic RAG retrieval. A speaking style guide, sixteen conversation examples, and a chapter behavior guide. Plus a Python upload script.

Story four: Voice ID and model config. Document the new voice ID, add a settings field, update the dashboard guide for V3 Conversational and Expressive Mode. Configure 16 Nikita-specific audio tags with descriptions in the Agent voice dashboard panel. Create a configure audio tags script as API backup. Verify the voice is IVC or designed — not PVC, which isn't supported with V3.

Story five: TTS settings optimization. Lower stability values across all chapters for V3 — chapter 1 goes from 0.8 to 0.55, chapter 5 from 0.4 to 0.35. The style parameter does NOT exist in agent TTS — only in standalone Multilingual v2. V3 uses stability modes: Creative at 0.0 to 0.3 for max expressiveness, Natural at 0.4 to 0.6 as recommended, Robust at 0.7 to 1.0 which suppresses audio tags.

Story six: Dashboard documentation. Write clear guides for the manual ElevenLabs dashboard configuration — voice selection, model selection, expressive mode toggle, audio tag setup, knowledge base upload, LLM verification, and agent security settings.

Story seven: First message enhancement. Add audio tags to Nikita's opening greeting on each call. Chapter 1 gets a dismissive or neutral tone. Chapters 2 and 3 get curious or happy. Chapters 4 and 5 get whispers or cheeky.

## System Prompt Architecture

The key architectural decision is a hybrid approach. The system prompt stays under 3,500 tokens and contains only per-user dynamic content — chapter, vices, memories, relationship score, mood, psyche state, and continuity. That's 10 sections totaling roughly 2,500 tokens of personalized content.

Static personality content moves to Knowledge Base. All three KB documents are uploaded as text-type docs — RAG retrieval is automatic, ElevenLabs decides what to surface based on conversation context. Document 1: speaking style guide with inner life patterns, psychology depth, attachment style, core wounds, and defense mechanisms. Document 2: 16 conversation examples with audio tags. Document 3: chapter behavior, extended backstory about Max and her father and the Berlin hacker scene, and NPC details for Lena, Viktor, Yuki, and Doctor Miriam.

This split works because the Knowledge Base is the same for all users. It never changes per call. Everything that changes per user stays in the dynamic system prompt. The RAG retrieval means conversation examples are pulled in contextually — only the relevant ones, not all sixteen every time.

## TTS Settings Changes

V3 is more expressive by default, so we lower stability across the board. Chapter 1 stability drops from 0.8 to 0.55 in the Natural upper range. Chapter 2 from 0.7 to 0.48 in Natural mid. Chapter 3 from 0.6 to 0.42 in Natural lower. Chapter 4 from 0.5 to 0.38 in Creative upper. Chapter 5 from 0.4 to 0.35 in Creative mid for maximum expressiveness. Speed gets slightly slower for more natural pacing. There is no style parameter in agent TTS — it does not exist. Audio tags and stability modes control expressiveness.

## Files Changing

Seven new files. An audio tags Python module. Three knowledge base markdown documents. An upload script. A configure audio tags script for API backup. And a test file for the audio tags module.

Ten files modified. The Jinja2 system prompt template section 3. The voice config module. The persona module. The TTS config module. The context module for dynamic variables. The settings module. The prompt builder for token budgets. Two documentation files. And multiple existing test files to update assertions from parenthetical to square bracket format. Note: models module does NOT change — there is no style field to add.

## Token Budget Update

The voice prompt token budget increases from 1,800 to 2,200 up to 2,800 to 3,500. This accounts for the expanded section 3 with audio tag instructions and conversation examples.

## Risks

Audio tags might get spoken as text instead of rendered as vocal expressions — we test with V3 before deploying. Knowledge Base might add latency — we monitor p95 after deploy. Token budget might get exceeded with the new examples — we measure with tiktoken and trim if needed. Existing tests will certainly break from the parenthetical-to-tag format change — we update all assertions systematically.

## What Stays the Same

The fallback chain: ready prompts, then cached voice prompt, then static voice agent config. The dynamic variables builder with 30-plus fields. The TTS config service pattern. All four server tools with their 2-second timeouts. The inbound call flow. The scoring system. The transcript manager. None of the voice backend infrastructure changes — this is purely about prompt quality and voice expressiveness.

## Dashboard Steps After Deploy

Manual configuration in the ElevenLabs dashboard: set voice to the new ID, select V3 Conversational model, toggle Expressive Mode on, add 16 audio tags with Nikita-specific descriptions in the Agent voice panel — each tag has a name and a description explaining when the agent should use it. Upload three knowledge base documents using the script. Verify Claude Sonnet 4.5 as the LLM. Enable system prompt override, first message override, voice ID, stability, speed, and similarity boost overrides in the agent security tab. Also run the configure audio tags script as an API backup for the dashboard tags.

## Dashboard Security Prerequisites (Override Fields)

Override fields in the `conversation_config_override` are **disabled by default** in ElevenLabs. Each must be individually enabled in the agent's **Security** tab before the override takes effect. If a field is not enabled, the override is silently ignored or returns an error.

| Override Field | Config Path | Must Enable |
|---------------|-------------|-------------|
| System prompt | `agent.prompt.prompt` | Yes — Security → Allow system prompt override |
| First message | `agent.first_message` | Yes — Security → Allow first message override |
| Voice ID | `tts.voice_id` | Yes — Security → Allow voice ID override |
| Stability | `tts.stability` | Yes — Security → Allow TTS parameter overrides |
| Similarity boost | `tts.similarity_boost` | Yes — Security → Allow TTS parameter overrides |
| Speed | `tts.speed` | Yes — Security → Allow TTS parameter overrides |

All six fields are used by our backend in three code paths:
- `context.py:to_elevenlabs_format()` — ConversationConfigBuilder (inbound dynamic config)
- `service.py:initiate_call()` — outbound call initiation
- `inbound.py:_get_conversation_config_override()` — inbound pre-call webhook

The `expressive_mode: true` flag is also set in all three paths but does not require a separate security toggle — it is controlled by the V3 Conversational model selection.

### Environment Variable

```env
ELEVENLABS_VOICE_ID=xDh1Ib47SaVb2H8RXsJf  # V3 Conversational voice
```

When `ELEVENLABS_VOICE_ID` is not set (None), the `voice_id` key is omitted from the TTS override and the dashboard default voice is used.
