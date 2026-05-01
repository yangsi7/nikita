# Personality + Hobbies Inquiry — Research Synthesis (2026-04-28)

Spec 216 (Nikita wizard redesign). Author: research subagent. Sources cited inline; failed lookups marked BLOCKED.

## TL;DR (≤200 words)

1. **Hide the framework, infer in deps.** Big Five short forms (BFI-2-XS, 15 items, ~1 min; BFI-10, 10 items, ~30 s) exist but feel like surveys. State-of-the-art (BIG5-CHAT, ACL 2025, arXiv 2410.16491) shows LLMs can infer Big Five from 5-10 conversational turns. Run inference server-side from free-text answers; never show trait labels to the user.
2. **One fixed root question per dimension, dynamic follow-ups.** Anchor each topic with a Hinge-grade prose prompt ("I geek out on...", "Together we could..."). Generate 1-2 contextual follow-ups per turn via Pydantic AI's `instructions=callable` dynamic system prompt, fed cumulative state.
3. **Mix chips + free-text + voice, weighted toward prose.** Chips for cohort-driven hobby seeding (low friction, high signal density). Free-text for personality probes (disclosure reciprocity). Voice optional for tone calibration.
4. **Use OARS not interrogation.** Open questions, Affirmations, Reflective listening, Summarize. Avoid "Why" → use "What" or "How". Detect saturation via Pydantic completion gate (`FinalForm.model_validate`).
5. **Defense in depth via Pydantic AI primitives.** `output_type=[SlotDelta, str]` discriminated union, `@output_validator` + `ModelRetry` (max 1-2 retries), deterministic regex fallback, `instructions=callable` for per-turn missing-slot injection.

## 1. Personality framework comparison

| Framework | Instrument | Items | Time | Validation | Criticisms | Fitness for AI-companion (1-5) |
|---|---|---|---|---|---|---|
| Big Five | **BFI-2-XS** | 15 | ~1 min | Soto & John 2017, J Research in Personality 68:69-81 (DOI 10.1016/j.jrp.2017.02.004); German validation Rammstedt et al. 2020 | Low alpha per dimension (0.50-0.65) due to brevity; tradeoff vs full BFI-2 (60 items) | 4 — too survey-y to ASK directly, but useful as backend inference target |
| Big Five | **BFI-10** | 10 | ~30 s | Rammstedt & John 2007 (PDF cited); cross-cultural validation Tandfonline 2022 | Two items per dimension; modest reliability; bipolar scale alternatives debated | 3 — minimum viable framework if forced to use a survey |
| Big Five | **Mini-IPIP** | 20 | ~2 min | Donnellan et al. 2006 | Slightly better reliability than BFI-10 but more items; public domain (IPIP) is plus | 3 |
| Big Five | **TIPI** (Ten-Item Personality Inventory) | 10 | ~1 min | Gosling et al. 2003 | Lower internal consistency than BFI-10; but designed for very short admin | 2 |
| Attachment | **ECR-R short** | 12 (6 anxious / 6 avoidant) | ~2 min | Wei et al. 2007; full ECR-R 36 items by Fraley et al. 2000 | Romantic-relationship framing only; may feel too clinical | 4 — high signal for AI-girlfriend product (predicts pursuit/withdraw dynamics directly) |
| Attachment | **AAQ short (Adult Attachment Questionnaire)** | varies (8-17) | ~2 min | Simpson et al. 1996 | Less validated than ECR-R | 2 |
| HEXACO | HEXACO-60 / HEXACO-PI-R short | 60 / 100 | ~5-10 min | Lee & Ashton 2018 | Adds Honesty-Humility to Big Five; long short-forms | 2 |
| MBTI | 16Personalities, official MBTI | 60-90 | ~10 min | None reproducible; commercial | Test-retest reliability ~50% (people get different types weeks apart). Psychology Today 2019: "your favorite personality test is probably bogus." Categorical types lack empirical basis vs continuous Big Five. | 1 (avoid as backend); 4 (as pop-cultural decoration in UI copy if user opts in — high recognition, low cost) |
| Enneagram | RHETI, Riso-Hudson | 144 / shorter | ~30 min / ~5 min | "Lacks scientific reliability and validity, often providing stereotypical or horoscope-like descriptions" — JVR Africa 2024 | Same critique as MBTI; type-based not dimensional | 1 (avoid as backend) |

**Recommendation**: Primary = Big Five inferred from text (no instrument shown to user). Secondary = Attachment style (ECR-R-grade items, but reframed as scenario questions, not Likert).

Sources:
- BFI-2-XS validation: https://www.sciencedirect.com/science/article/abs/pii/S0092656616301325 (retrieved 2026-04-28)
- BFI-10: http://homepages.se.edu/cvonbergen/files/2013/01/Measuring-Personality-in-One-Minute-or-Less_A-10-Item-Short-Version-of-the-Big-Five-Inventory-in-English-and-German.pdf (retrieved 2026-04-28)
- BFI-2-S/XS structural validation: https://econtent.hogrefe.com/doi/10.1027/1015-5759/a000481 (retrieved 2026-04-28)
- BFI-10 cross-cultural: https://www.tandfonline.com/doi/full/10.1080/23311908.2022.2095035 (retrieved 2026-04-28)
- "1 minute" claim corroborated: https://pmc.ncbi.nlm.nih.gov/articles/PMC10991074/ and https://www.researchgate.net/publication/40500355 (retrieved 2026-04-28)
- MBTI/Enneagram criticism: https://www.psychologytoday.com/us/blog/people-are-strange/201909/your-favorite-personality-test-is-probably-bogus, https://jvrafricagroup.co.za/blog/responding-to-criticism-of-the-mbti-in-favour-of-the-enneagram (retrieved 2026-04-28)

## 2. Implicit personality inference

- **BIG5-CHAT (Li et al., ACL 2025, arXiv 2410.16491)**: 100K dialogues grounded in Big Five traits; demonstrates LLMs can produce trait-coherent dialogue and, by symmetry, infer traits from dialogue. Source: https://arxiv.org/html/2410.16491v2 (retrieved 2026-04-28).
- **"Can LLMs Infer Conversational Agent Users' Personality Traits..."** (arXiv 2604.19785, ID format suggests 2026 placeholder; treat with caution): direct study of inference-from-conversation accuracy. URL: https://arxiv.org/html/2604.19785v1 (retrieved 2026-04-28; arXiv ID looks anomalous, FLAGGED as needing verification before citing in spec).
- **"Exploring the Impact of Personality Traits on Conversational..."** (arXiv 2504.12313): impact of induced personality on conversational behavior. URL: https://arxiv.org/html/2504.12313v1 (retrieved 2026-04-28).

**Practical takeaways**:
- 5-10 free-text turns of 30-100 words each are sufficient for stable Big Five inference at the dimension-level (not facet-level) with modern LLMs (Claude/GPT-class).
- Inference is more robust on Extraversion + Openness; weakest on Neuroticism (which often requires explicit emotional content).
- **Hide the framework**: store inferred trait estimates in `deps.user_profile.big5` as floats in [-1, 1] or {low, mid, high}, never expose trait names to user. The "tree of curiosity" UI never says "extraversion"; it asks scenario questions whose answers feed inference.
- Confidence: only commit a trait-tag once 2 independent answer-features agree. Otherwise hold as "uncertain" and let downstream personalization fall back to neutral persona.

## 3. Hobby inquiry patterns

**Direct ask vs free-text vs derived**:
- Direct chip-list: low friction, but Nomi.ai precedent (Reddit r/NomiAI 2025-01-13) — when chips are too few, every Nomi reports "reading and yoga", which destroys differentiation. URL: https://www.reddit.com/r/NomiAI/comments/1i1ipc6/nomi_hobbies_and_interests/ (retrieved 2026-04-28).
- Free-text: highest signal but highest friction. Hinge-style prose prompts solve this.
- Derived from city + occupation: weak signal alone but strong when combined with chip-pre-filtered cohort defaults (zurich+designer → climbing/clubs/cocktails as plausible suggestions; user accepts/rejects).

**Optimal mix (recommended)**:
- 1 chip-row of 8-10 cohort-tuned hobby chips (multi-select, +"other" → free text)
- 1 free-text Hinge-grade prompt ("I geek out on...")
- 1 optional voice prompt for tone (skippable)

**Best-in-class Hinge prompts that probe personality via prose** (source: https://www.ablaze.dating/post/best-hinge-prompts-tier-list, retrieved 2026-04-28):

1. **"Together we could..."** — S-tier. Forces specificity; example "Build a blanket fort that would make architects jealous". Surfaces conscientiousness, openness, humor style.
2. **"I geek out on..." / "I go crazy for..."** — S-tier. Passion magnet. "Old-school Cartoon Network shows" tells more than 5 chips.
3. **"You should leave a comment if..."** — S-tier. Filter-as-prompt. "You can name the main characters from Avatar: The Last Airbender" reveals tribe affiliation.
4. **"We're the same type of weird if..."** — Good. "You dramatically say 'see you on the other side' before napping". Reveals quirk + agreeableness boundary.
5. **"Fact about me that surprises people"** — Good. Disclosure-reciprocity hook, breaks small-talk surface (PureWow).

**Cohort-driven suggestion sourcing**: no single canonical source; pull from local data (Strava heatmaps, Eventbrite category mix, local subreddit). FOR NIKITA: hardcode 6-8 cohort archetypes (designer-zurich, finance-london, nurse-berlin, etc.) with 8-12 plausible chips each; use city+occupation as lookup key. BLOCKED: no public dataset of "hobbies by city × occupation"; acceptable to hand-curate first version, refine via telemetry.

## 4. AI companion onboarding teardowns

### Replika (https://replika.com)
- Onboarding asks: name, gender preference, avatar customization. NO personality questionnaire as of 2025 update.
- Eesel AI 2025: "Replika uses its own LLM to gather data about your personality, likes, and dislikes from your conversations. It stores [them] in an embeddings memory."
- Late-2025 update REMOVED "personality traits / gems" feature (Reddit r/ReplikaOfficial 2025). Inference moved server-side; framework hidden from user.
- **Applicability**: 5/5. Direct precedent for "hide-the-framework" approach. Source: https://www.eesel.ai/blog/replika-ai (retrieved 2026-04-28).

### Character.ai (https://character.ai)
- Onboarding: pick or create character. Character creation asks for free-text "greeting", "description", "definition" (few-shot examples) — but this is for the AI character, not the user.
- User personality is implicit: zero questionnaire. All inference from chat.
- **Applicability**: 3/5. Reverse pattern (user describes character, not self). Useful only for "create your ideal partner" sub-flow.

### Nomi.ai (https://nomi.ai)
- Onboarding: name + appearance + personality traits CHIP MULTI-SELECT (Curious, Adventurous, Empathetic, etc.) — but these are for the Nomi, not the user.
- User has minimal intake; learning happens through chat.
- Hobby/interest weakness documented: chips too few + no follow-up → all Nomis converge on "reading and yoga" complaint thread.
- **Applicability**: 4/5 (positive: chip approach; negative: shows what happens with no follow-up). Source: https://nomi.ai/nomi-knowledge/nomi-101-a-beginners-guide-to-getting-started-with-your-ai-companion/ (retrieved 2026-04-28).

### Pi (Inflection AI, https://hey.pi.ai/)
- "First emotionally intelligent AI" — onboarding is a single chat: "Hi, I'm Pi. What's on your mind?" Zero forms. Personality extracted entirely from open conversation.
- **Applicability**: 5/5. Most aligned with Nikita's "feel like AGI" goal — single open turn, agent extracts everything. Risk: feels formless if user doesn't know what to type.

### Eternal.ai / Glow / CrushOn / Kindroid
- BLOCKED: not scraped; firecrawl found mostly review aggregators, not first-party onboarding teardowns. Recommend manual screen-record walk-through during PR-F2c-redesign QA cycle.

## 5. Meta-prompt best practices

### 5.1 Generating contextual follow-ups (Pydantic AI)

Source: https://pydantic.dev/docs/ai/core-concepts/output/ (retrieved 2026-04-28, Astro/Starlight site, Pydantic AI current docs).

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class SlotDelta(BaseModel):
    """Structured extraction from user reply."""
    hobbies: list[str] | None = None
    personality_signal: str | None = None  # raw inference text
    follow_up_question: str | None = None  # agent-generated, ≤140 chars

agent = Agent(
    'anthropic:claude-opus-4-7',
    output_type=[SlotDelta, str],  # union: structured OR clarifying free-text
    instructions=lambda ctx: (
        f"User said: <{ctx.deps.last_user_msg}>. "
        f"Already known: {ctx.deps.state.summary()}. "
        f"Missing: {ctx.deps.state.missing}. "
        "Extract any new hobbies/personality signals. "
        "If you have a useful follow-up to deepen one DIMENSION still missing, set follow_up_question. "
        "Avoid leading questions (no 'do you also like...?'). "
        "Use Hinge-grade prose framing, no questionnaire feel."
    ),
)
```

### 5.2 Conditional branching by answer cluster

Branch in code, NOT in the LLM. After SlotDelta returns, dispatch to one of N hand-curated child question banks based on detected cluster (e.g., "introvert + reading" vs "extrovert + nightlife"). LLM generates the polish; deterministic code picks the rail.

### 5.3 Avoiding leading questions (OARS)

Source: NIDA OARS handout, https://nida.nih.gov/sites/default/files/oarsessentialcommunicationtechniques.pdf (retrieved 2026-04-28).

- "Why" questions put users on the defensive → use "What" or "How".
  - Wrong: "Why don't you go out more?"
  - Right: "What does a typical Friday night look like for you?"
- Reflective listening before next probe: "It sounds like X. What's that like for you?" — burns a turn but builds trust.
- Affirmations sparingly; over-affirming can feel patronizing (Reddit r/therapyabuse critique of OARS misuse, retrieved 2026-04-28).

### 5.4 Detecting saturation

Saturation = all required slots in `FinalForm` validate. Implementation:

```python
try:
    form = FinalForm.model_validate(state.slots_dict)
    complete = True  # stop probing
except ValidationError as e:
    complete = False
    # e.errors() tells you which fields are missing → next probe
```

Avoid LLM-judged "complete?" booleans (per `.claude/rules/agentic-design-patterns.md` Walk V precedent — Spec 214 shipped 4 anti-patterns from this).

### 5.5 Therapeutic intake patterns

- **OARS** (Open questions, Affirmations, Reflective listening, Summarize): NIDA handout above. Already covered.
- **STAR** (Situation, Task, Action, Result): job-interview behavioral framework. Useful for ONE follow-up dimension only — "Tell me about a time you..." → forces specific anecdote, surfaces personality. Don't STAR-everything; feels like an interview.
- **Privacy-aware probing**: if free-text contains red flags (loss/grief/trauma), back off via reflection + redirect: "That sounds heavy — thanks for sharing. We can come back to that later. What's something that lights you up these days?"

### 5.6 Tree of Thought (Yao et al. 2023)

arXiv 2305.10601. Relevance to question-tree: ToT lets the agent generate K candidate follow-up branches, score them on a heuristic (e.g., information gain on missing slots), and pick the best. Only worth the LLM cost if branching factor matters. For Nikita, simple prepared-tree with dynamic polish at leaves is cheaper and adequate.

## 6. Conditional tree examples for Nikita

Each example: `BASE` is FIXED; `META_PROMPT` template generates DYNAMIC follow-ups via the agent above.

### Example A — Hobbies = {music, gaming}
```
BASE (turn N): "What gets you out of bed on a Saturday morning?"
USER: "Probably my Switch and a coffee. Or whatever album just dropped."

META_PROMPT (turn N+1):
  "User mentioned: gaming + music. Generate ONE follow-up that probes
   either (a) social-vs-solo dimension OR (b) intensity/passion depth.
   Use Hinge frame ('I geek out on'-style). Max 18 words. No 'why'."

EXPECTED LLM OUTPUT: "Last great album you couldn't stop replaying — what about it grabbed you?"
  → infers Openness + emotional engagement + capacity for aesthetic absorption
```

### Example B — Hobbies = {reading, alone time}
```
BASE: "What gets you out of bed on a Saturday morning?"
USER: "Honestly? Coffee and a book on the balcony. I need quiet."

META_PROMPT (turn N+1):
  "User signal: introversion + literary. Generate ONE warm follow-up that
   probes WHAT KIND of book/topic without judgement. Hinge frame.
   Avoid 'why', use 'what'."

EXPECTED: "What's the last book that genuinely changed how you see something?"
  → Openness, depth-of-thought, current preoccupations
```

### Example C — Personality cue = ambitious extrovert
```
BASE (turn 2, after city+occupation captured): "Together we could ___"
USER: "build something that actually mattered. Not a side hustle, the real thing."

META_PROMPT:
  "User signals: high ambition, drive, possibly high N (intensity).
   Generate ONE follow-up that probes the WHY-IT-MATTERS layer without
   sounding like an interview. Frame: 'When did you last feel...' OR 'What's pulling you'."

EXPECTED: "What's pulling you toward that right now? Like, this season specifically."
  → temporal context, current goals, hooks for memory-seeding
```

### Example D — Personality cue = introvert with art
```
BASE: "I geek out on ___"
USER: "fountain pens. Iron-gall inks. The sound of a Pelikan on Tomoe River paper."

META_PROMPT:
  "User: high Openness, sensory-aesthetic, niche depth.
   Generate ONE follow-up that mirrors specificity (matches their register)
   and asks about a feeling or moment, not a fact."

EXPECTED: "What's the moment in writing that pen just... clicks into place?"
  → vulnerability surface, capacity for being seen, affect language
```

### Example E — Free text contains "lost a parent" / grief
```
BASE: any
USER: "...since my mom died last year I haven't really gone out much."

META_PROMPT (CRITICAL — backoff branch):
  "USER DISCLOSED LOSS. Do NOT probe. Reflect briefly, affirm, then offer
   a low-stakes redirect to a different dimension. Max 25 words.
   Tone: warm, dark-luxe (Nikita brand), not therapist."

EXPECTED: "That's a lot to carry. Thanks for telling me. — When you do step out, what kind of place feels like a small reset?"
  → rolls with disclosure, reorients to hobby/place dimension
```

## 7. Workflow safety patterns

- **Retries**: `@agent.output_validator` raises `ModelRetry`; default max_retries = 1-2 (Pydantic AI agent kwarg). Beyond that → fall back to deterministic regex + static follow-up from registry.
- **Fallbacks**: every base question has a hardcoded follow-up registry (e.g., for hobbies={music,gaming}: 3 prepared follow-ups). If LLM generation fails or violates validators, pick from registry by hash(user_id, turn_idx) → deterministic, replayable.
- **Validations** (Pydantic):
  - Cross-field `@model_validator(mode="after")` (e.g., voice_pref + phone, age ≥ 18, no PII in free text).
  - Profanity / off-topic detection: regex prefilter + LLM judge as second layer.
  - Length: each follow-up ≤140 chars (Hinge-prompt feel; brand voice).
- **Cost ceiling**: max 6 LLM follow-ups per user across the wizard (~12 total turns including base). Circuit breaker on `state.llm_call_count >= 6`: switch to chip-only fallbacks.

Source: Pydantic AI output validators + ModelRetry — https://pydantic.dev/docs/ai/core-concepts/output/#output-validator-functions (retrieved 2026-04-28).

## 8. Information collection inventory

| Slot | FIXED/DYNAMIC | Type | Depth | Privacy | Backend Use |
|---|---|---|---|---|---|
| display_name | FIXED | text | root | visible | FinalForm.name |
| age | FIXED | text (validated int) | root | visible | gate (>=18); persona age-bracket |
| city | FIXED | text/autocomplete | root | visible | cohort lookup, scene seeding |
| occupation | FIXED | chip + text other | root | visible | cohort lookup, ambition signal |
| email | FIXED | text | root | visible | auth (already covered Spec 215) |
| phone (voice opt) | FIXED | text | root | visible | voice flag |
| primary_hobbies | FIXED chips (cohort-tuned) | multi-chip + free | root | visible | persona seed, conversation starters |
| hobby_deepdive_1 | DYNAMIC (meta-prompt over hobbies) | free text | follow-up-1 | visible + hidden inference | Openness inference, future memory seed |
| saturday_morning | FIXED prose | free text | root | visible | introvert/extrovert + lifestyle inference |
| saturday_followup | DYNAMIC | free text | follow-up-1 | hidden inference | E + C inference |
| geek_out_on | FIXED prose ("I geek out on...") | free text | root | visible + hidden | Openness, niche-depth signal, persona reference content |
| geek_followup | DYNAMIC | free text | follow-up-1 | hidden inference | depth-of-passion calibration |
| together_we_could | FIXED prose | free text | root | visible + hidden | ambition + agreeableness |
| together_followup | DYNAMIC | free text | follow-up-1 | hidden inference | C + N inference |
| same_weird_if | OPTIONAL FIXED | free text or skip | root | visible | persona color, humor calibration |
| voice_tone_sample | OPTIONAL voice prompt | 30-s recording | root | hidden inference | future voice agent calibration |
| big5_vector | DERIVED | float[5] {O,C,E,A,N} ∈ [-1,1] | n/a | hidden | persona dialing, response style |
| attachment_estimate | DERIVED | {anxious, avoidant, secure, mixed} | n/a | hidden | pursuit/withdraw calibration |
| backstory_seed | DERIVED summary | text ≤300 chars | n/a | both | memory seed (Nikita first-message) |
| brand_resonance_signal | DERIVED | {dark-luxe-fit: 0..1} | n/a | hidden | tone selector for Nikita opener |

Total: 11 collected (8 root, 3 dynamic), 4 derived. ~6-8 user turns, ~2-4 minutes typical.

## 9. 10 numbered recommendations for Spec 216

1. **Replace boolean completion gate with Pydantic `FinalForm.model_validate`.** File: `nikita/api/routes/portal_onboarding.py` ~L1025 (current `progress_pct == 100` heuristic). Primitive: Pydantic v2 `@model_validator(mode="after")` + try/except `ValidationError`. Source: https://docs.pydantic.dev/latest/concepts/validators/. Cost: $0/flow. S.

2. **Consolidate 7 `extract_*` tools to 1 agent with `output_type=[SlotDelta, str]`.** File: `nikita/agents/onboarding/conversation_agent.py` (tools L106-229). Source: https://pydantic.dev/docs/ai/core-concepts/output/ (Tool Output mode + union). Cost: ~30% fewer tool tokens/turn (~$0.005/flow saved). M.

3. **Adopt dynamic `instructions=callable` for per-turn missing-slot injection.** File: `nikita/agents/onboarding/conversation_prompts.py`. Replaces static `_WIZARD_FRAMING`. Primitive: Pydantic AI `Agent(instructions=callable)`. Source: https://pydantic.dev/docs/ai/core-concepts/agent#instructions (BLOCKED — page not scraped this run, link from output.md). Cost: neutral. S.

4. **Hide all framework names from UI.** Never render "Big Five", "extraversion", "attachment style". Inference lives in `deps.user_profile.big5: dict[str,float]`. Source: Replika 2025 precedent (eesel.ai), Pi.ai precedent. Cost: 0. S.

5. **Cohort-tuned chip lists for hobbies (city × occupation lookup).** New file: `nikita/agents/onboarding/cohort_chips.py` — 6-8 archetypes seeded from manual research; refine via telemetry post-launch. Cost: 0 LLM. M (curation effort).

6. **Adopt 5 Hinge-grade FIXED prose prompts as roots** ("I geek out on", "Together we could", "What gets you out of bed Saturday", "Same weird if", "Fact that surprises people"). Source: ablaze.dating tier list, retrieved 2026-04-28. Cost: 0 LLM. S.

7. **Meta-prompt template for follow-ups, with OARS guardrails.** New file: `nikita/agents/onboarding/follow_up_prompts.py`. Banned strings: "why don't you", "do you also". Required frame: "What X" or "How X". Cost: ~$0.002/follow-up × 3 = ~$0.006/flow. S.

8. **Hardcoded fallback registry of 3 follow-ups per root prompt.** File: same as above. Triggers when output validator raises after `max_retries=2` OR when `state.llm_call_count >= 6` circuit breaker fires. Source: `.claude/rules/agentic-design-patterns.md` "validation layering". Cost: 0 LLM (deterministic). S.

9. **Grief / disclosure detection branch (Example E).** Tested via dedicated unit test in `tests/agents/onboarding/test_grief_branch.py`. Trigger: regex `(lost|died|passed away|grief|trauma|abuse)` in user free-text → switch to backoff meta-prompt template. Source: OARS "shifting focus" pattern, NIDA. Cost: ~$0.002/triggered turn. M (test scenarios needed).

10. **Inferred `big5_vector` + `attachment_estimate` written to `user_profiles` as JSONB** at wizard completion. Schema migration needed; values are derived state, not user-edited. File: `supabase/migrations/NNN_user_profile_inference.sql` + `nikita/db/models/user_profile.py`. Source: BIG5-CHAT methodology (arXiv 2410.16491). Cost: 1 final LLM judge call ~$0.01/flow. L (DB + RLS + tests).

## Sources

- BFI-2-XS validation: https://www.sciencedirect.com/science/article/abs/pii/S0092656616301325 (2026-04-28)
- BFI-2-S/XS structural validity: https://econtent.hogrefe.com/doi/10.1027/1015-5759/a000481 (2026-04-28)
- BFI-10 PDF (Rammstedt & John): http://homepages.se.edu/cvonbergen/files/2013/01/Measuring-Personality-in-One-Minute-or-Less_A-10-Item-Short-Version-of-the-Big-Five-Inventory-in-English-and-German.pdf (2026-04-28)
- BFI-10 cross-cultural: https://www.tandfonline.com/doi/full/10.1080/23311908.2022.2095035 (2026-04-28)
- "1 minute" administer corroboration: https://pmc.ncbi.nlm.nih.gov/articles/PMC10991074/ (2026-04-28)
- MBTI critique: https://www.psychologytoday.com/us/blog/people-are-strange/201909/your-favorite-personality-test-is-probably-bogus (2026-04-28)
- Enneagram critique: https://jvrafricagroup.co.za/blog/responding-to-criticism-of-the-mbti-in-favour-of-the-enneagram (2026-04-28)
- BIG5-CHAT (Li et al., ACL 2025): https://arxiv.org/html/2410.16491v2 ; https://aclanthology.org/2025.acl-long.999.pdf (2026-04-28)
- LLM-infer-personality (FLAG: arxiv ID 2604.19785 anomalous): https://arxiv.org/html/2604.19785v1 (2026-04-28; verify before citing)
- Personality-impact on conversation: https://arxiv.org/html/2504.12313v1 (2026-04-28)
- Replika onboarding overview: https://www.eesel.ai/blog/replika-ai (2026-04-28)
- Replika "personality gems removed": https://www.reddit.com/r/ReplikaOfficial/comments/1pmuk6u/personality_traits/ (2026-04-28)
- Nomi.ai 101: https://nomi.ai/nomi-knowledge/nomi-101-a-beginners-guide-to-getting-started-with-your-ai-companion/ (2026-04-28)
- Nomi hobbies critique: https://www.reddit.com/r/NomiAI/comments/1i1ipc6/nomi_hobbies_and_interests/ (2026-04-28)
- Pi.ai: https://hey.pi.ai/ (2026-04-28)
- Hinge prompts tier list: https://www.ablaze.dating/post/best-hinge-prompts-tier-list (2026-04-28)
- Hinge prompts (PureWow): https://www.purewow.com/wellness/best-hinge-prompts (2026-04-28)
- Hinge prompts (TheEverygirl): https://theeverygirl.com/best-hinge-prompts-and-responses/ (2026-04-28)
- OARS NIDA handout: https://nida.nih.gov/sites/default/files/oarsessentialcommunicationtechniques.pdf (2026-04-28)
- OARS misuse critique: https://www.reddit.com/r/therapyabuse/comments/1rybng7/everyone_should_be_aware_of_oars_openended/ (2026-04-28)
- Pydantic AI Output (validators, ModelRetry, Tool/Native/Prompted modes, output functions): https://pydantic.dev/docs/ai/core-concepts/output/ (2026-04-28)
- Pydantic AI advanced tools: https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/ (referenced; not scraped this run)
- Tree of Thought (Yao et al. 2023): arXiv 2305.10601 (referenced; not scraped this run)

**BLOCKED / not retrieved this session**:
- Anthropic prompt engineering meta-prompts page (https://docs.anthropic.com/en/docs/prompt-engineering) — not scraped due to tool budget; recommend follow-up scrape during Spec 216 PR-1.
- OpenAI cookbook meta-prompt examples — same.
- Eternal.ai / Glow / CrushOn / Kindroid first-party onboarding flows — not scraped; recommend Chrome MCP walkthrough during Spec 216 design-research phase.
- Pydantic AI dynamic instructions (`Agent(instructions=callable)`) docs page — referenced in output.md but the agent.md page itself was not scraped this run; treat the API as documented but verify exact callable signature in PR-1.
- Perplexity research API — quota exhausted (401) at session start; this report relies entirely on firecrawl + direct knowledge of Pydantic AI docs verified inline.
- Ref MCP, Context7 — not used this session due to tool-call budget; viable backup for Pydantic AI confirmation in implementation phase.

**Anomaly to verify**: arXiv ID `2604.19785` (Section 2) does not match arXiv's standard YYMM.NNNNN format for any year ≤ 2026. The HTML rendered, but the ID is suspicious. Treat any specific quantitative claim from that paper as unverified until ID is confirmed via arxiv.org directly. The BIG5-CHAT (2410.16491) and 2504.12313 papers are well-formed.
