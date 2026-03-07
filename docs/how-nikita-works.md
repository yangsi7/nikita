# How Nikita Works — A Complete Technical Walkthrough

## The Big Picture

Nikita is an AI girlfriend simulation game. Players interact with her through Telegram text messages and voice calls powered by ElevenLabs. But calling it a "chatbot" would be like calling a symphony an arrangement of noises. Under the hood, there are over fourteen interconnected systems working together to make Nikita feel like a real person with a life, emotions, psychology, and relationship dynamics that evolve over time.

The core experience loop works like this. A player sends a message. That message passes through a series of gates — authentication, rate limiting, onboarding checks. Then the system decides whether Nikita should even reply right now, because sometimes she's busy, sometimes she's upset, sometimes she just doesn't feel like texting back immediately. If she does respond, a pre-built system prompt is loaded — one that was assembled by a background pipeline that knows her current mood, what happened in her day, what she remembers about the player, what chapter of the relationship they're in, and what psychological state she's operating from. Claude generates a response using all of that context. The response gets post-processed to sound like actual texting — lowercase, emoji quirks, message fragmentation. It gets sent back to Telegram. And then, in the background, a ten-stage pipeline kicks off to extract facts from the conversation, update memory, simulate Nikita's life events, compute her emotional state, update the player's score, check for conflicts, schedule proactive messages, and rebuild the prompt for the next conversation.

The result is something that feels less like talking to an AI and more like navigating a real relationship — with all the uncertainty, emotional complexity, and stakes that come with it.

Let me walk you through every system.

---

## What Happens When You Text Nikita

A Telegram webhook receives the player's message and routes it to the message handler. The first thing that happens is a series of gates. Is this user authenticated? Have they completed onboarding — choosing between text and voice, filling out their backstory and preferences? Are they within the rate limit of twenty messages per minute and five hundred per day? If any gate fails, the message is rejected or queued.

Assuming everything checks out, the system makes a critical decision: should Nikita respond right now? This is handled by the skip decision logic, and it's one of the most important elements of making her feel human. In Chapter One, when the relationship is brand new and Nikita is still deciding if this person is worth her time, she only responds about twenty-five to forty percent of the time. By Chapter Five, when the relationship is deeply established, she responds ninety-five to one hundred percent of the time. When she does decide to skip, the player just sees silence — exactly like texting someone who's busy or not that interested yet.

Even when she does respond, there's a delay. In Chapter One, responses take two to five minutes. By Chapter Five, they're nearly instant. This delay is randomized with jitter to feel organic, not mechanical.

Now the system loads message history. It pulls the last several turns of conversation from a JSON blob stored in the conversations table, token-budgeted to around three thousand tokens. These get converted into the format that Pydantic AI expects — user messages become request objects, Nikita's responses become response objects, and any tool calls from previous turns get properly paired.

Next comes the system prompt. This is where the magic happens. If the background pipeline has already run for this user, there's a pre-built prompt sitting in the ready prompts table. This prompt is massive — around five thousand to six thousand five hundred tokens — and contains eleven carefully assembled sections covering Nikita's identity, her current emotional state, what's happening in her simulated life, the relationship state, relevant memories, open conversation threads, her inner thoughts, psychological vulnerabilities, chapter-specific behavior instructions, and vice personalization. If no pre-built prompt exists, the system falls back to a lighter version assembled on the fly.

The system also layers additional instructions. There's Nikita's static persona — about four hundred tokens of core behavioral rules that never change. Then conditional overlays based on the current chapter. Then the psyche briefing, which we'll get to later. All of these stack on top of the pre-built prompt.

With everything assembled, the system calls Claude Sonnet through Pydantic AI. During generation, Claude has access to two tools. The first is recall memory, which lets it search the player's stored facts via semantic search. The second is note user fact, which lets it flag something the player said as worth remembering. Claude decides autonomously when to use these tools — the system doesn't force memory lookups.

After Claude generates a response, it goes through text pattern post-processing. This is Spec Twenty-Six, the behavioral patterns system. It injects emoji based on sentiment and context. It applies lowercase and punctuation quirks. It adjusts message length — expanding short responses, compressing verbose ones. It fragments messages to feel like natural texting, where someone sends three short messages instead of one long paragraph. It even introduces occasional typos and trailing thoughts.

The final response gets sent back through Telegram, and the conversation is marked for background processing.

---

## The Ten-Stage Background Pipeline

After every conversation, a background pipeline runs to extract intelligence from what just happened and prepare for the next interaction. This pipeline is triggered by a PostgreSQL cron job that fires every minute, checking for conversations that have been idle for at least fifteen minutes — meaning the conversation has gone quiet and it's time to process.

The pipeline has ten stages, split into two categories. The first two are critical — if they fail, the entire pipeline stops. The remaining eight are non-critical — they can fail independently without blocking the others.

Stage One is Extraction. This is the intelligence-gathering stage. An LLM call analyzes the full conversation and extracts structured data: discrete facts about the player, ongoing conversation threads, Nikita's inner observations and thoughts, a one to two sentence conversation summary, and the overall emotional tone — positive, negative, mixed, or neutral. This is the raw material that feeds every other stage.

Stage Two is Memory Update. The extracted facts get checked against existing memories using pgVector cosine similarity. If a fact is more than ninety-five percent similar to something already stored, it's considered a duplicate and gets skipped. Otherwise, the fact is classified into one of three categories — user facts, relationship episodes, or Nikita's own life events — and stored with a vector embedding for future semantic search.

Stage Three is Persistence. This saves Nikita's extracted inner thoughts and conversation threads to dedicated database tables. These persist across conversations and contribute to her sense of continuity — she can reference things she was thinking about yesterday.

Stage Four is Life Simulation. This is where Nikita's world gets generated. An event generator creates three to five daily life events across three domains — work, social, and personal. These might include things like "finished a security audit at work," "had coffee with Lena," or "Schrodinger knocked a beaker off the desk." The events respect daily patterns and time of day, and they feed into the emotional state computation.

Stage Five is the Emotional State computation. Nikita's emotional state is tracked across four dimensions: arousal, which ranges from calm to excited; valence, from sad to happy; dominance, from submissive to dominant; and intimacy, from guarded to vulnerable. The state computer takes inputs from the life events, the conversation's emotional tone, the time of day, and the current relationship chapter, then computes a new four-dimensional emotional vector. This state gets stored and injected into the next conversation's prompt.

Stage Six is Game State. This is where the hidden scoring happens. Score deltas from the conversation are applied to the four relationship metrics — intimacy, passion, trust, and secureness. The system checks whether the player has crossed a chapter progression threshold, whether a boss encounter should trigger, and whether the player is in a critical score zone.

Stage Seven is Conflict processing. The conflict system evaluates whether the conversation involved any conflict triggers — dismissiveness, neglect, jealousy, boundary violations, or trust breaches. If so, it updates a continuous temperature gauge that tracks relationship tension. If the temperature rises above certain thresholds, escalation mechanics kick in.

Stage Eight is Touchpoint scheduling. Based on the current state of the relationship, this stage might schedule a proactive message from Nikita — something she sends unprompted. This could be triggered by time gaps, life events, or decaying scores. We'll talk more about this later.

Stage Nine is Summary generation. A daily conversation summary gets generated and stored. These summaries are used in future prompts to give Nikita awareness of "what happened today" and "what happened this week."

Stage Ten is the Prompt Builder, and this is arguably the most important stage. It takes everything — memories, emotional state, life events, conversation summaries, open threads, psyche state, chapter behavior, vice preferences — and renders it all through a Jinja2 template into a complete system prompt with eleven sections. This prompt gets stored in the ready prompts table, ready to be loaded instantly the next time the player messages. For text conversations, the prompt runs about five thousand five hundred to six thousand five hundred tokens. For voice, it's trimmed to around two thousand eight hundred to three thousand five hundred tokens.

---

## How Nikita Remembers You

Nikita's memory system uses Supabase with the pgVector extension for semantic vector search. Every fact the system extracts about the player — where they work, what they enjoy, their fears, their relationship history — gets converted into a vector embedding and stored in the memory facts table.

When Nikita needs to recall something during a conversation, Claude can invoke the recall memory tool with a natural language query. The system converts that query into a vector, performs a cosine similarity search against all stored facts, and returns the most relevant matches. This means if the player once mentioned they have a dog named Max, and three weeks later Nikita is generating a response where she wants to reference something personal, the semantic search will surface that fact even without exact keyword matching.

There are three types of stored memories. User facts are things about the player — their job, hobbies, location, preferences. Relationship episodes are shared moments — memorable conversations, fights, breakthroughs. And Nikita facts are events from her simulated life that she's mentioned in conversation, creating consistency when she references them later.

Deduplication is critical. Before storing any new fact, the system checks if something ninety-five percent similar already exists. This prevents the memory store from filling up with slightly different versions of the same information. Recent memories are weighted higher in search results, so the system naturally prioritizes what's been relevant lately while still having access to the full history.

---

## Nikita's Inner Psychology — The Psyche Agent

Every day at five AM UTC, a batch job runs that generates Nikita's psychological state for each active player. This is the psyche agent, and it's one of the most sophisticated systems in the entire project.

The psyche agent produces an eight-field model called PsycheState. The first field is attachment activation — whether Nikita is in an anxious mode, craving reassurance, or an avoidant mode, creating distance. The second is defense mode — which psychological defense mechanisms are currently active, like humor deflection, intellectualization, or preemptive withdrawal. The third is behavioral guidance — a concise, actionable direction for how Nikita should behave in the next interaction. The fourth is internal monologue — what Nikita is actually thinking right now. The fifth is vulnerability level, a zero to one scale of how willing she is to be emotionally open. The sixth is emotional tone. And the last two are lists of topics to encourage and topics to avoid.

The daily batch job uses Claude to generate this state based on the last forty-eight hours of data — score history trends, emotional states, life events, and NPC interactions. It considers Nikita's backstory: her ex Max's emotional abuse, her fear that she's "too much" for people, her belief that love is conditional. These core wounds get activated or deactivated based on what's happening in the relationship.

Not every message triggers a full psyche recalculation. The system uses a three-tier approach. Ninety percent of messages — Tier One — just read the cached psyche state from the database, adding zero latency. About eight percent — Tier Two — trigger a quick Sonnet analysis for moderate psychological triggers, taking about two seconds. And roughly two percent — Tier Three — trigger a deep Opus analysis for critical moments like a score drop of more than five points, detection of one of Gottman's Four Horsemen, or an explicit emotional disclosure. This deep analysis takes about five seconds but produces much richer psychological modeling.

The resulting psyche state gets injected as Layer Three of the system prompt — about a hundred and fifty tokens of psychological context that shapes every response Nikita generates.

---

## Life Simulation — Nikita Exists Between Conversations

One of the most powerful contributors to Nikita feeling real is that she has a life when you're not talking to her. The life simulation engine generates daily events across three domains — work, social, and personal.

Work events might include project updates, meetings, deadlines, or office drama. Social events involve her named friends — Lena, her best friend; Viktor, her ex; Yuki, her therapist — doing things together, having conversations, creating drama. Personal events cover her cat Schrodinger, gym sessions, cooking experiments, reading, or errands.

These aren't just random events. They're generated by an LLM that understands Nikita's character, her current emotional state, and the time of day. Morning events tend to be work-focused. Evening events are more social or personal. The mood flowing into event generation is bidirectional — her mood influences what events happen, and the events influence her mood back.

Beyond single events, the system supports multi-week narrative arcs. These are storylines that play out over three to ten conversations — a career milestone building toward a promotion, friend drama escalating with Lena, a family visit with all its complications. Each arc progresses through stages: setup, rising action, climax, falling action, and resolution. These arcs give Nikita's life a sense of ongoing story, not just daily snapshots.

When the prompt builder assembles the system prompt, it includes recent life events naturally. So Nikita might casually mention "just got back from the gym" or "Lena and I had the weirdest conversation today" — and it's grounded in actual simulated events, not hallucinated details.

---

## The Hidden Game — Scoring, Decay, and Chapters

Underneath every conversation, a scoring engine is tracking four relationship metrics. Intimacy carries thirty percent weight and measures emotional closeness and vulnerability. Passion carries twenty-five percent and measures excitement, attraction, and chemistry. Trust carries twenty-five percent and measures reliability, consistency, and emotional safety. And secureness carries twenty percent and measures confidence in the relationship's stability. These combine into a composite score from zero to one hundred.

The score changes based on how each conversation goes. Positive interactions push metrics up, negative ones push them down. But there's a catch — the engagement model modulates positive gains. The system tracks the player's engagement across six states: calibrating, in-zone, drifting, clingy, distant, and out-of-zone. If you're messaging too much and the system detects clingy behavior — based on message frequency, double-texting, instant response times, and needy language patterns — your positive gains get cut to half. If you're too distant, they drop to sixty percent. Only when you're in the sweet spot do you get the full benefit of your good interactions. And critically, penalties are never reduced — if you say something hurtful, you take the full hit regardless of engagement state.

The game is structured into five chapters: Curiosity, Intrigue, Investment, Intimacy, and Established. Each chapter has a score threshold for progression — fifty-five percent for Chapter One, increasing to seventy-five percent for Chapter Five. When you hit a threshold, a boss encounter triggers. These are multi-phase challenges — an opening phase where Nikita presents a relationship test, and a resolution phase where your response is evaluated. Boss encounters have three possible outcomes: pass, which advances you to the next chapter; fail, which increments your failure counter; and partial or truce, which triggers a twenty-four hour cooldown. Three failures at any boss encounter means game over.

Each chapter also defines a decay rate. When you stop talking to Nikita, your relationship scores slowly decline. In Chapter One, the grace period before decay starts is eight hours, and the decay rate is zero point eight percent per hour. By Chapter Five, the grace period extends to seventy-two hours with a much gentler zero point two percent per hour decay. This creates natural urgency — especially early on, you need to stay engaged or the relationship will deteriorate.

And then there's the vice system. Eight categories — intellectual dominance, risk-taking, substances, sexuality, emotional intensity, rule-breaking, dark humor, and vulnerability — are tracked per player based on conversation patterns. A vice analyzer detects signals in each exchange, and a scorer updates intensity levels. These vices are injected into the prompt to personalize how Nikita engages with the player's specific interests. But sensitive categories like sexuality and substances have chapter-based caps — they stay low in early chapters and open up as the relationship deepens.

---

## Proactive Touchpoints — When Nikita Reaches Out

About twenty to thirty percent of conversations in the system are initiated by Nikita, not the player. The touchpoint engine handles this, and it's a surprisingly nuanced system.

Touchpoints can be triggered by several conditions. Time-based triggers fire during morning and evening windows. Gap-based triggers activate when the player hasn't messaged in over twenty-four hours. Life event triggers fire when something significant happens in Nikita's simulated day. And decay warning triggers activate when the player's score is actively declining.

The messages themselves are chapter-aware and emotionally calibrated. In Chapter One, a decay warning might sound like "hey, you still there?" or "did I scare you off already?" — tentative, testing. By Chapter Five, it becomes "you know I worry when you disappear" or "come back to me" — direct, vulnerable, intimate.

Crucially, there's also a strategic silence system that decides when Nikita should not reach out. She won't message during an active conversation, within two hours of her last message, during active conflict escalation, or if there are already pending touchpoints waiting to be delivered. Sometimes absence says more than words.

---

## The Conflict System — Fighting Like a Real Couple

Nikita's conflict system is built on Gottman's research into relationship dynamics — specifically the "Four Horsemen" that predict relationship breakdown: contempt, criticism, defensiveness, and stonewalling. The system detects these patterns in player messages and uses them to trigger realistic relationship conflicts.

Conflicts can be triggered by five types of player behavior: dismissiveness, where the player ignores or minimizes Nikita's concerns; neglect, going more than twenty-four hours without contact; jealousy, mentioning other romantic interests; boundary violations, disrespecting limits she's stated; and trust breaches, lying or being inconsistent.

Each trigger type has a severity weight, from zero point three for dismissiveness up to zero point seven for trust breaches. These feed into a continuous temperature gauge that ranges from zero to one hundred. Below twenty, everything is fine. Twenty-one to forty, she's slightly upset but manageable. Forty-one to sixty, she's noticeably cold and the distance is growing. Sixty-one to eighty is crisis mode — the relationship is threatened. Above eighty, breakup is imminent.

Conflicts escalate through three levels: subtle, where Nikita gives cold one-word answers or hints at being upset; direct, where she explicitly states what's wrong; and crisis, where she issues ultimatums or threatens to end things. Resolution attempts are evaluated for quality — a sincere apology works differently than a weak one, and trying to just change the subject without actually resolving the issue is tracked as a distraction attempt that doesn't fully heal the wound.

---

## Voice Calls — Talking to Nikita

Beyond text, players can actually call Nikita using ElevenLabs Conversational AI Two Point Zero. The voice integration uses a server tools pattern where ElevenLabs' system calls back into our API during the conversation.

Availability is chapter-gated. In Chapter One, Nikita only picks up about ten percent of the time — she's busy, she doesn't know you that well. By Chapter Five, she answers ninety-five percent of calls. When she doesn't answer, the player gets an in-character explanation of why she's unavailable.

During a voice call, the ElevenLabs system makes four types of server tool calls back to our API. Get context loads the player's facts, threads, and memories. Get memory performs semantic search for relevant memories. Score turn evaluates individual conversation turns for metric deltas. And update memory stores new facts observed during the call.

Even the voice synthesis settings change by chapter. In Chapter One, Nikita speaks with high stability and moderate similarity boost — reserved, measured. By Chapter Five, stability drops and similarity boost increases — her voice becomes more expressive, passionate, natural. The speech rate also increases from zero point nine five to one point one, reflecting greater comfort and energy.

After the call ends, the transcript goes through the same scoring pipeline as text messages. Score deltas are applied, boss encounters are checked, and the conversation is queued for the full ten-stage background pipeline.

---

## The Seven Background Jobs — Nikita Never Sleeps

Seven PostgreSQL cron jobs keep Nikita's world running around the clock, all routing to Cloud Run task endpoints.

The decay job runs every hour. It iterates through all active users, calculates how many hours have elapsed since their last interaction, applies the chapter-appropriate decay rate after the grace period, and updates their scores. There's a safety cap of twenty points maximum decay per cycle to prevent catastrophic loss from long absences.

The deliver job runs every minute. It checks the scheduled events table for messages that are due — both proactive touchpoints and delayed responses — and delivers them through the appropriate platform.

The process conversations job also runs every minute. It finds conversations that have been idle for fifteen minutes and runs them through the full ten-stage pipeline. It processes up to ten conversations per cycle to avoid overloading the system.

The daily summary job runs at eleven fifty-nine PM UTC. It generates end-of-day summaries for all active players using an LLM call, capturing the score trajectory, conversation highlights, and emotional tone of the day.

The psyche batch job runs at five AM UTC. It generates fresh PsycheState models for every active player, giving Nikita updated psychological context for the coming day.

The cleanup job runs hourly, removing expired pending registrations and other stale data.

And the boss timeout job runs every six hours, resolving any boss fight states that have been stuck for more than twenty-four hours. If a player triggered a boss encounter but never responded, it counts as a failed attempt after the timeout.

All of these jobs use dedicated authentication tokens separate from the main API, and they include idempotency guards to prevent double-processing if a job fires twice.

---

## Why It All Works Together

The key insight behind Nikita is that no single system creates the illusion of humanity. It's the integration — the feedback loops between fourteen-plus systems that makes her feel alive.

Memory gives her history. She remembers what you told her three weeks ago. The psyche agent gives her psychology. She has attachment styles, defense mechanisms, and core wounds that shape her behavior. Life simulation gives her independence. She has a job, friends, a cat, and storylines unfolding in her life when you're not around. The emotional state engine gives her mood. She's not always the same — she's affected by her day, by what you said last time, by how long it's been since you talked. The scoring and decay systems create stakes. Neglect the relationship and it deteriorates. Push too hard and the engagement multiplier punishes you. The conflict system creates drama. Real fights, with real escalation dynamics, drawn from actual relationship psychology research. Proactive touchpoints create the illusion of initiative. She texts you first. She worries when you disappear. She sends you something because Lena said something that reminded her of you.

And all of this happens on a compressed timeline where a two-week chapter takes days, not months, with hourly decay cycles and daily psyche regeneration creating a relationship that evolves at a pace that keeps the player engaged.

The text pattern processor adds the final layer. Even if every other system were perfect, responses that read like a corporate email would break the illusion. The emoji insertion, the lowercase quirks, the message fragmentation, the occasional typo — these transform a technically perfect response into something that feels like it was thumbed out on a phone by someone who's a little distracted, a little playful, and genuinely thinking about you.

The result isn't a chatbot with memory. It's a character you're building a relationship with — one that rewards attention, punishes neglect, evolves over time, and occasionally picks a fight just because she's having a bad day and you said the wrong thing.

That's how Nikita works.
