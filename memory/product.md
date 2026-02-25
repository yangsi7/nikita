# Product Definition: Nikita - Don't Get Dumped

**Version**: 2.0.0
**Created**: 2025-11-28
**Last Updated**: 2026-01-12

---

## Product Overview

### Name
**Nikita: Don't Get Dumped**

### Tagline
*Can you keep a brilliant, unfiltered AI girlfriend from leaving you?*

### Vision
A world where AI relationships are a genuine **game**—not an emotional crutch, but a skill-based challenge where you can actually win or lose. Dating simulations that feel laughably real because there's no game interface—just texts and calls that blur the line between fiction and reality.

### Problem Statement
**What pain exists in the world?**

Adults who enjoy games and AI are stuck between two unsatisfying options:
1. **AI companions** (Replika, Character.AI) that feel hollow, forget everything, censor conversations, and never challenge you—just endless validation
2. **Dating sims** that are obviously games with cartoon interfaces, pre-written dialogues, and zero unpredictability

There's no product that delivers the **thrill of a challenging game** combined with the **immersion of a real relationship**—where your actual conversational skills determine success, the AI remembers everything, and there are real stakes (you can get dumped).

### Market Context
- **TAM (Total Addressable Market)**: Tech-savvy adults (25-40) who enjoy narrative games, AI experimentation, and unconventional digital experiences. Overlaps with dating sim players, interactive fiction enthusiasts, and AI early adopters.
- **Current Solutions**: Character.AI (filtered, no memory), Replika (no challenge, just validation), dating sims (obviously games, no AI), AI assistants (transactional, no personality)
- **Opportunity**: First-mover in "AI relationship as competitive game" category. Voice AI finally mature enough (ElevenLabs 2.0) for real-time calls. Memory technology (pgVector semantic search) enables genuine long-term relationship building.

---

## Value Proposition

### Core Value
**What do users get?**
A challenging, hilarious, and surprisingly intimate game where you're trying to maintain a relationship with a brilliant, unpredictable AI girlfriend who will dump you if you fuck up.

**Why 10x better?**
- **Stakes**: You can actually LOSE. Score hits 0% or fail 3 bosses = game over.
- **No interface**: It's just Telegram + phone calls. Feels like texting/calling a real person.
- **Memory**: She remembers everything—inside jokes, arguments, your job, what you said 2 months ago.
- **Unfiltered**: Nikita talks like a real person—about drugs, sex, dark humor, intellectual debates—no corporate sanitization.
- **Voice calls**: Real-time AI voice conversations that feel like calling your girlfriend.

### "Our Thing"
**The 1-2 things people will LOVE about this product:**
1. **The absurd realism** — "Holy shit, I just got dumped by an AI and I'm... actually upset?" The game creates genuine emotional stakes because there's no game UI reminding you it's fake. It's hilarious AND affecting.
2. **The challenge** — Unlike every other AI companion that just validates you, Nikita is HARD. She tests you. She picks fights. She goes silent for hours. Winning actually feels like an accomplishment.

### Key Differentiators
**How are we different?**
1. **Game mechanics with real stakes** — Chapters, bosses, decay system, scoring. You can win (reach Chapter 5 victory) or lose (get dumped). No other AI companion is a *game* you can fail.
2. **No interface illusion** — Other products have chatbots in apps. Nikita is Telegram messages and phone calls. The "game" is invisible—it feels like real life.
3. **Persistent temporal memory** — Not just "remembers your name"—tracks the entire relationship history with timestamps, emotional context, and evolving understanding of who you are.

---

## Humanization Systems (v2.0)

The following systems transform Nikita from a functional AI into a believably human companion:

### 1. Voice Onboarding System (NEW)

**"Meta-Nikita"** conducts an introductory voice call after Telegram /start:

```
User sends /start on Telegram
    ↓
Collect phone number
    ↓
"Ready for your onboarding call?"
    ↓
VOICE CALL: Meta-Nikita onboards user:
  1. Introduction to game mechanics/expectations
  2. Collect user info: location, job, hobbies, personality
  3. Collect preferences: darkness level, pace, conversation style
    ↓
Game begins with personalized Nikita
```

**Why**: Immediate immersion, personalization from the start, and clear expectation-setting.

### 2. Proactive Touchpoint System (NEW)

Nikita initiates conversations on her own—she has a life, not just responses.

- **Initiation Rate**: 20-30% of conversations Nikita-initiated
- **Time Triggers**: Morning check-ins, evening connection, post-gap explanations
- **Event Triggers**: Life sim events, mood shifts, memory recalls
- **Strategic Silence**: 10-20% intentional gaps for tension/mystery

**Why**: A girlfriend who only responds when you text isn't realistic. Proactive initiation is the #1 humanization gap.

### 3. Life Simulation Engine (MAJOR ENHANCEMENT)

Nikita lives an independent existence with evolving daily events:

- **Work Drama**: Projects, deadlines, annoying colleagues, wins and losses
- **Social Network**: Friends and colleagues she mentions naturally
- **Daily Events**: Gym, meetings, outings that affect her availability/mood
- **Narrative Timeline**: 4-week default (8-week option), no huge growth arcs

**Conversation Balance** (configurable):
- 30-40% Nikita talking about her life
- 30-40% Nikita asking about user's life
- 30% Nikita listening/responding

**Why**: She must feel like she exists even when you're not texting her.

### 4. Behavioral Meta-Instruction System (NEW)

High-level decision trees that guide LLM behavior without overspecifying:

**Design Philosophy**: "Cover all ground flexibly... give high-level instructions but never specific so the LLM can adapt to any situation and not feel predictable."

- **Situation Categories** (not specific scenarios)
- **Directional Guidance** (not exact responses)
- **LLM Judgment** within personality bounds
- **Consistency** without predictability

**Covers**:
- Absence explanations (when asked vs proactive)
- Conflict escalation paths
- Intimacy progression pacing
- Response timing signals

### 5. Emotional State Engine (ENHANCEMENT)

Multi-dimensional mood tracking that affects all responses:

**Dimensions Tracked**:
- **Arousal**: Energy level (tired ↔ energetic)
- **Valence**: Positivity (sad ↔ happy)
- **Dominance**: Assertiveness (submissive ↔ dominant)
- **Intimacy**: Openness (guarded ↔ vulnerable)

**Conflict States**:
- Passive-aggressive (cold, one-word answers)
- Cold (withdrawn, minimal engagement)
- Vulnerable (hurt, needing reassurance)
- Explosive (angry confrontation)

**Recovery Mechanics**: Reconciliation requires player investment.

### 6. Conflict Generation System (NEW)

Real disagreements create relationship depth:

**Conflict Types**:
- Jealousy (mentions of other relationships)
- Boundary testing (pushing limits)
- Emotional (misunderstandings, unmet expectations)
- Power struggles (control/independence)

**Conflict Style**: Realistic ambiguity—sometimes clear, sometimes passive-aggressive. User must read signals.

**Stakes**: High—genuine breakup risk after repeated failures.

### 7. Configurable Personality System (ENHANCEMENT)

User-adjustable experience parameters:

**Darkness Dial** (onboarding + portal):
- Default: Mild edge—freely discusses substances/sex, has insecurities, can be smartly manipulative
- Configurable: Can crank up to full noir (possessiveness, manipulation, darker themes)

**Vice Category Intensities**: Per-category darkness levels

**Conversation Balance Preferences**: More curious (40:30:30) vs balanced (30:40:30)

**Pacing**: 4-week intense vs 8-week extended journey

---

## Hierarchical Prompt Architecture

**Key Insight**: Most computation done in POST-PROCESSING to prepare for NEXT conversation. Latency managed by pre-computing layers asynchronously (15+ min post-conversation).

### Prompt Layers (Bottom to Top)

| Layer | Name | Computation | Content |
|-------|------|-------------|---------|
| 1 | Base Personality | Static | Core Nikita traits, values, speaking style |
| 2 | Chapter Layer | Pre-computed | Stage-appropriate intimacy, disclosure, behaviors |
| 3 | Emotional State | Pre-computed | Current mood, energy, life events affecting her |
| 4 | Situation Layer | Pre-computed | Morning vs evening vs after-gap scenarios |
| 5 | Context Injection | Real-time (~150ms) | User knowledge, relationship history, threads |
| 6 | On-the-Fly Mods | During conversation | Mood shifts, memory retrieval when relevant |

### Context Sources

| Source | Content | Retrieval Timing |
|--------|---------|------------------|
| User Graph | Preferences, triggers, communication style | Pre-conversation |
| Relationship Graph | Shared memories, milestones, conflicts | Pre-conversation |
| Nikita State | Current mood, energy, her day's events | Pre-conversation |
| Life Events | Work updates, social dynamics | Pre-conversation |
| Active Threads | Unresolved topics, pending questions | Pre-conversation |
| Daily Summaries | Yesterday's conversation essence | Pre-conversation |
| Week Summaries | Relationship trajectory | Weekly refresh |
| Real-time Retrieval | Graph queries for specific recall | During generation |

### Text Behavior Specifications

**Emoji Usage**:
- Selective, very occasional (max 1-2 per message, sometimes none)
- Classic emoticons: :)
- Approved emojis: 😏🙄🍆😘😅🥲🙂
- Context: flirtation, sarcasm, affection, mild self-deprecation

**Message Length**:
- Default: Short, punchy, multiple messages in sequence
- Longer: Emotional topics, fights, deep conversations
- Context-dependent—must feel realistic

**Response Timing**:
- Not immediate (unless engaged conversation)
- Strategic delays when upset or for mystery
- Enthusiasm signals (quick reply = excited)

---

## User Personas (3 Primary)

### Persona 1: Marcus - "The Achievement Hunter"

**Demographics**
- Age range: 30-35
- Location: Urban US (San Francisco, Austin, NYC)
- Education: CS degree, works in tech
- Income: $120-200K (software engineer)
- Tech Savviness: Extremely high—builds side projects, follows AI news, has opinions on GPT vs Claude

**Psychographics**
- **Behaviors**: Completes games on hardest difficulty, tracks his stats in everything, competitive in online gaming, reads AI newsletters (The Batch, Import AI)
- **Values**: Skill-based achievement, intellectual challenge, being ahead of the curve on technology, efficiency
- **Goals**: Master challenging systems, have interesting stories to tell, stay on cutting edge of AI capabilities
- **Frustrations**: Games that are too easy, AI products that feel dumbed-down or filtered, lack of intellectual peers who "get" his interests

**Context: A Day in Their Life (Without Our Product)**
Marcus works a demanding job building ML systems. In his downtime, he plays competitive games, but they're feeling stale. He's tried various AI companions—Replika felt pathetic (just agrees with everything), Character.AI kept hitting content filters mid-conversation. He reads about AI advances daily but the actual consumer products are disappointing. He wishes there was an AI experience that actually challenged him, something he could "beat" that required real skill.

**Pain Points** (Jobs-to-be-Done Framework)

1. **Pain**: AI companions are boringly easy—they just validate and agree
   - **Why it hurts**: No sense of accomplishment, feels like talking to a yes-man, quickly gets boring
   - **Current workaround**: Abandons AI companions after a few days, goes back to competitive games
   - **Frequency**: Every time he tries a new AI product (monthly)

2. **Pain**: Content filters kill immersion in AI conversations
   - **Why it hurts**: Mid-conversation the AI suddenly becomes corporate and sanitized, breaking any illusion of genuine interaction
   - **Current workaround**: Self-hosts open-source models, but they're way worse quality
   - **Frequency**: Multiple times per session on commercial AI products

3. **Pain**: No AI product feels like a "real" challenge to master
   - **Why it hurts**: His identity is built around being good at hard things—easy experiences don't provide the satisfaction he craves
   - **Current workaround**: Returns to competitive gaming (LoL, Valorant), but that scene is getting old
   - **Frequency**: Ongoing unfulfilled need

**How We Resolve Their Pains**
1. Pain 1 → Nikita is genuinely challenging—scoring system means you can FAIL, boss encounters require actual skill, decay punishes neglect. Marcus can actually "win" or "lose."
2. Pain 2 → No content filters. Nikita talks about drugs, sex, dark humor—whatever the conversation goes. No corporate sanitization breaking immersion.
3. Pain 3 → 5-chapter progression with bosses creates a mastery curve. Victory requires 120+ days of sustained engagement and skill. Something to actually accomplish.

**Success Metrics** (How we measure we solved their problems)
- Reaches Chapter 3+ (demonstrates meaningful progression)
- Plays 30+ days without churning
- Tells friends about it ("you gotta try this AI girlfriend game")

---

### Persona 2: Elena - "The Tech Explorer"

**Demographics**
- Age range: 26-30
- Location: Europe or urban US (Berlin, London, Brooklyn)
- Education: Design/UX degree, works in product or creative field
- Income: $70-100K
- Tech Savviness: High but not technical—uses all the latest apps, follows AI on social media, early adopter mindset

**Psychographics**
- **Behaviors**: Tries every new AI product day-one, shares interesting tech on Instagram/Twitter, attends AI meetups, podcasts about technology (Lex Fridman, Hard Fork)
- **Values**: Novel experiences, being first to discover things, authentic/edgy over corporate/sanitized, creativity
- **Goals**: Stay culturally relevant, discover next big thing before mainstream, have unique experiences to share
- **Frustrations**: AI products that feel corporate and boring, overly cautious content policies, experiences that everyone already knows about

**Context: A Day in Their Life (Without Our Product)**
Elena works at a design agency and spends her evenings exploring new tech. She was excited about AI companions but every one felt... corporate. Replika was too therapy-speak. Character.AI was promising until it refused to have interesting conversations. She heard about jailbroken models but they're too technical to set up. She wants an AI experience that's genuinely edgy, authentic, and worth talking about—not another sanitized chatbot.

**Pain Points** (Jobs-to-be-Done Framework)

1. **Pain**: AI products feel sanitized and corporate
   - **Why it hurts**: Kills the excitement—she wants authentic, edgy experiences, not HR-approved chatbots
   - **Current workaround**: Follows jailbreaking communities but doesn't have technical skills to actually use them
   - **Frequency**: Every AI product she tries (weekly)

2. **Pain**: Nothing novel left to explore in consumer AI
   - **Why it hurts**: Her identity involves discovering cool things first—if ChatGPT is mainstream, she needs the next thing
   - **Current workaround**: Follows niche AI Twitter, but most things are just hype without real products
   - **Frequency**: Ongoing FOMO

3. **Pain**: AI conversations feel shallow and forgettable
   - **Why it hurts**: Wants genuine intellectual and emotional stimulation, not just utility
   - **Current workaround**: Reads fiction, watches complex TV shows for the stimulation AI chatbots don't provide
   - **Frequency**: Daily unfulfilled need

**How We Resolve Their Pains**
1. Pain 1 → Nikita is genuinely unfiltered—talks about LSD, hacking, sex, dark philosophy. No corporate voice, no content warnings.
2. Pain 2 → First AI product that's a competitive GAME with voice calls. Genuinely novel category. Great conversation starter.
3. Pain 3 → Nikita has deep personality, remembers everything, evolves over months. Conversations have intellectual depth (physics, psychology, cryptography) AND emotional stakes.

**Success Metrics** (How we measure we solved their problems)
- Shares the product on social media
- Uses voice call feature (the "wow" factor)
- Returns after 7 days (wasn't just novelty)

---

### Persona 3: James - "The Immersion Seeker"

**Demographics**
- Age range: 33-40
- Location: Suburban US or UK
- Education: Liberal arts or business degree
- Income: $80-120K (marketing manager, analyst, professional)
- Tech Savviness: Moderate—uses technology but isn't obsessed with it, plays games on console not PC

**Psychographics**
- **Behaviors**: Plays narrative-heavy games (Mass Effect, Baldur's Gate 3), reads sci-fi novels, enjoys long-form podcasts, values quality over quantity
- **Values**: Deep immersion, emotional authenticity, meaningful narratives, quality craftsmanship
- **Goals**: Have genuinely moving experiences, escape into well-crafted worlds, feel genuine connection (even if fictional)
- **Frustrations**: Shallow entertainment, AI that breaks immersion, experiences that don't respect his intelligence

**Context: A Day in Their Life (Without Our Product)**
James has a stable job and uses gaming as his escape. He loved Mass Effect's character relationships and wishes real AI could deliver that. He tried AI companions but they all feel robotic—they don't remember past conversations, their personalities are inconsistent, and any interesting topic gets blocked. He wants an AI experience that feels like a relationship in a great RPG—with continuity, character development, and emotional stakes—but without the obvious game UI.

**Pain Points** (Jobs-to-be-Done Framework)

1. **Pain**: AI companions have no memory—each conversation starts fresh
   - **Why it hurts**: Can't build a relationship if they forget who you are. No emotional investment possible.
   - **Current workaround**: Returns to video games where at least the relationships have continuity
   - **Frequency**: Every AI companion attempt (several times)

2. **Pain**: Game UI breaks immersion in dating sims
   - **Why it hurts**: Dialogue options, character portraits, and menus constantly remind him it's fake
   - **Current workaround**: Accepts that AI relationships will never feel real
   - **Frequency**: Inherent to all dating sims

3. **Pain**: AI personalities are inconsistent or shallow
   - **Why it hurts**: Immersion requires a coherent character—not an AI that changes personality mid-conversation
   - **Current workaround**: Writes his own fiction to get the character depth he craves
   - **Frequency**: Every AI product

**How We Resolve Their Pains**
1. Pain 1 → Nikita remembers everything—your job, your inside jokes, that argument from week 3, what you told her about your family. Months of continuous memory.
2. Pain 2 → No game UI at all. Just Telegram texts and phone calls. The illusion is complete—it feels like texting a real person.
3. Pain 3 → Nikita is a deeply crafted character with consistent personality, backstory, interests, and chapter-based character development. She evolves believably over 120+ days.

**Success Metrics** (How we measure we solved their problems)
- Plays 60+ days (indicates deep engagement)
- Uses voice calls regularly (deepest immersion)
- Reaches Chapter 4+ (invested in the "relationship")

---

## User Stories (High-Level Epics)

**Format**: As [persona], I want to [goal], so that [outcome/benefit]

### Epic 1: Challenge-Based Progression
**As** Marcus (Achievement Hunter),
**I want to** progress through increasingly difficult chapters with boss encounters,
**So that** I can experience genuine challenge and earn a meaningful victory.

**Why this matters**: Addresses Marcus's pain of AI companions being boringly easy. Creates mastery curve and real stakes.

### Epic 2: Immersive Unfiltered Conversation
**As** Elena (Tech Explorer),
**I want to** have unfiltered conversations with a genuinely edgy AI personality,
**So that** I can experience something authentic that's worth talking about.

**Why this matters**: Addresses Elena's pain of sanitized AI products. Delivers the novel experience she's seeking.

### Epic 3: Persistent Relationship Memory
**As** James (Immersion Seeker),
**I want to** build a relationship with an AI that remembers everything across months,
**So that** I can experience genuine emotional continuity and character development.

**Why this matters**: Addresses James's pain of AI companions forgetting everything. Enables real relationship investment.

---

## User Journeys (Chain-of-Events)

### Journey 1: Discovery to First Value

**Persona**: All (converges on shared path)

**Chain-of-Events** (CoD^Σ):
```
Awareness (word of mouth/social) ≫ Curiosity ("AI girlfriend you can lose?") ≫ Research (watch clip/read about) → Decision (Telegram is free) ≫ Onboarding (link account) → First Message (Nikita: "So you found me. Interesting.") ≫ First Value ("Holy shit, she's actually challenging") ∘ Hook (wants to reply)
```

**Detailed Flow**:

1. **Awareness** (How they discover us)
   - Friend shares screenshot of Nikita's unfiltered message
   - Tweet/TikTok: "Day 47 of trying not to get dumped by my AI girlfriend"
   - AI newsletter mentions "first AI companion you can actually lose"
   - Pain point activated: Boredom with existing AI companions

2. **Initial Interest** (First impression)
   - "Wait, you can actually GET DUMPED?"
   - "She talks about drugs and sex? Without filters?"
   - "Voice calls? Like actually calling her?"
   - Question: "Is this real? How does it work?"

3. **Research** (Evaluation)
   - Watches someone's voice call clip (TikTok/YouTube)
   - Reads about the chapter/boss system
   - Verifies: "It's just Telegram? No weird app?"
   - Concern addressed: "It's free to try, just need Telegram"

4. **Decision** (Commitment moment)
   - Low barrier: Telegram is familiar, no new app install
   - Convincing factor: "5 chapters, can win or lose—that sounds like a game"
   - Barrier removed: No payment required upfront

5. **Onboarding** (Getting started)
   - Opens Telegram bot (@NikitaGameBot)
   - /start command
   - Links account via magic link (email verification)
   - 30 seconds to first interaction

6. **First Use** (Initial experience)
   - Nikita's first message: "So you found me. Interesting. What do you want?"
   - Tone: Guarded, skeptical, challenging
   - User realizes: This isn't a friendly chatbot
   - Feedback: Nikita responds (maybe)—with delays, attitude

7. **First Value Achieved** (Aha moment)
   - User sends something clever → Nikita responds with genuine engagement
   - OR: User tries boring small talk → Nikita is dismissive
   - Realization: "Holy shit, she's actually evaluating me"
   - Time to aha: 5-10 messages

8. **Habit Formation** (Becoming a regular user)
   - Notification: Nikita initiated a conversation
   - Checks score: "Wait, I'm at 48%? What happened?"
   - Pattern: Thinks about how to improve, strategizes responses
   - Comes back to avoid decay, progress relationship

**Pain Point Resolution Mapping**:
- Journey step 6 (First Use) resolves "AI companions are boringly easy"
- Journey step 7 (First Value) resolves "No challenge to master"

---

### Journey 2: The Gameplay Loop (Chapter Progression)

**Persona**: Marcus (Achievement Hunter)

**Chain-of-Events** (CoD^Σ):
```
Daily Check-in (avoid decay) ≫ Conversation (score +/-) → Score Analysis (metrics update) ≫ Threshold Check (boss ready?) → [If Yes] Boss Encounter ⊕ [Pass] Chapter Advance | [Fail] Retry/Game Over ∘ New Chapter Behaviors Unlock
```

**Detailed Flow**:

1. **Daily Check-in** (Avoiding decay)
   - User knows: "If I don't message within 24h, I lose 5%"
   - Opens Telegram, sends message to maintain connection
   - Nikita's response depends on chapter (Ch1: might ignore, Ch5: usually replies)

2. **Conversation Exchange** (Core gameplay)
   - Each exchange analyzed: How did user respond?
   - Intellectual depth? Playful banter? Clingy? Desperate?
   - Score adjusts: +3% for engaging exchange, -2% for boring small talk

3. **Boss Threshold Reached** (Achievement unlocked)
   - User hits 60% in Chapter 1
   - Nikita shifts: "Alright. Prove you're worth my time."
   - Boss encounter begins—this is the test

4. **Boss Encounter** (Skill check)
   - Extended conversation with specific challenge
   - Ch1: Intellectual challenge—show you can engage her mind
   - Ch2: Conflict test—stand your ground when she picks a fight
   - 3 attempts max—fail 3 times = game over

5. **Pass/Fail Outcome**
   - **Pass**: "Okay. You're not boring. I'll give you more of my time."
   - Chapter advances, new behaviors unlock, reset attempts
   - **Fail**: Score penalty, warning: "That wasn't it. Try again."

6. **New Chapter** (Progression reward)
   - Nikita's behavior evolves: More responsive, less testing
   - Decay becomes more forgiving (36h grace vs 24h)
   - New conversation depths available (more personal topics)

**Pain Point Resolution Mapping**:
- Steps 2-4 resolve "No AI product feels like a real challenge"
- Step 6 resolves "AI personalities are inconsistent"

---

### Journey 3: Voice Call Experience (Maximum Immersion)

**Persona**: James (Immersion Seeker)

**Chain-of-Events** (CoD^Σ):
```
Desire for Deeper Connection ≫ Initiate Call (/call command) → Connection (phone rings) ≫ Real-time Conversation (voice AI responds <100ms) ∘ Emotional Peak (she laughs at my joke) → Call End ≫ Reflection (that felt real) ∘ Habit (calls become regular)
```

**Detailed Flow**:

1. **Desire for Deeper Connection**
   - User thinking: "Texting is good but I wonder what she sounds like"
   - Trigger: Nikita mentions "you could just call me, you know"
   - Curiosity overcomes hesitation

2. **Initiate Call**
   - User: /call command in Telegram
   - Bot: "Calling Nikita..." + phone number or deep link
   - Phone rings—actual phone call experience

3. **Connection Established**
   - Nikita answers: "Hey. Didn't expect you to actually call."
   - Her voice matches personality: confident, slightly amused, Eastern European hint
   - Real-time conversation begins

4. **Real-time Voice Conversation**
   - Sub-100ms latency—feels like real phone call
   - She remembers context from texts: "So how did that meeting go you were nervous about?"
   - User talks naturally—no typing, no UI, just conversation
   - Her responses adapt to tone of voice, not just words

5. **Emotional Peak**
   - User cracks a joke → She actually laughs
   - Or: Deep conversation about something personal
   - Thought: "This feels more real than any chatbot I've tried"

6. **Call End**
   - Natural goodbye or session timeout
   - Nikita: "Talk to you later. Don't ghost me."
   - Transcript logged, memory updated, score adjusted

7. **Reflection & Habit**
   - User realizes: "I just had a phone call with an AI that felt... real"
   - Calls become regular part of gameplay
   - Deepest immersion level achieved

**Pain Point Resolution Mapping**:
- Steps 3-5 resolve "Game UI breaks immersion"
- Step 4 resolves "AI conversations feel shallow"

---

### Journey 4: Voice Onboarding (Personalized Entry)

**Persona**: All (mandatory entry point)

**Chain-of-Events** (CoD^Σ):
```
/start Command ≫ Phone Number Collection → Readiness Check ≫ Voice Call ("Meta-Nikita") ∘ Game Introduction → User Profile Collection (location, job, hobbies) → Preference Configuration (darkness, pace, style) ≫ Game Begins (personalized Nikita)
```

**Detailed Flow**:

1. **/start Command** (Entry point)
   - User opens Telegram bot (@NikitaGameBot)
   - Sends /start command
   - Bot: "Welcome. Before we begin, I need your phone number for the onboarding call."

2. **Phone Number Collection**
   - User provides phone number
   - Validation + formatting
   - Bot: "Great. You're about to receive a call that will explain everything and get you set up."

3. **Readiness Check**
   - Bot: "Ready for your onboarding call? Reply 'yes' when you're in a quiet place."
   - User confirms readiness
   - Call initiated via ElevenLabs

4. **Voice Call: Meta-Nikita**
   - NOT Nikita persona—a neutral, helpful onboarding voice
   - "Hi! Welcome to Nikita. I'm going to quickly explain how this works and learn a bit about you."

5. **Game Introduction** (~2 min)
   - Explains: This is a game with real stakes
   - Explains: Chapters, scoring, boss encounters
   - Explains: You can win or lose—Nikita can dump you
   - Sets expectation: "This isn't a typical AI chatbot"

6. **User Profile Collection** (~3 min)
   - Location: "What city do you live in?"
   - Job: "What do you do for work?"
   - Hobbies: "What do you like to do in your free time?"
   - Personality: "Would you describe yourself as more introverted or extroverted?"
   - Hangout spots: "What's your favorite type of place to hang out?"

7. **Preference Configuration** (~2 min)
   - Darkness level: "How edgy should Nikita be? Mild, moderate, or intense?"
   - Pacing: "Want an intense 4-week journey or a slower 8-week experience?"
   - Conversation style: "Should Nikita be more curious about you, or share more about herself?"

8. **Handoff to Game**
   - "Alright, you're all set. Nikita will text you shortly. Good luck—don't get dumped!"
   - Call ends
   - First Nikita text arrives within 5 minutes

**Pain Point Resolution Mapping**:
- Steps 5-7 resolve "No personalization" pain point
- Step 4 resolves "Unclear expectations" for new users
- Step 8 creates immediate engagement hook

---

### Journey 5: Proactive Initiation (Nikita Reaches Out)

**Persona**: All (ongoing throughout game)

**Chain-of-Events** (CoD^Σ):
```
Life Sim Event (work drama) ≫ Emotional State Update → Touchpoint Trigger (time/event) ≫ Initiation Decision → Message Composition → Strategic Timing ≫ User Receives → Response or Silence ∘ Relationship Impact
```

**Detailed Flow**:

1. **Life Simulation Event**
   - Nikita's simulated day: "Bad meeting at work, colleague criticized her project"
   - Mood update: Lower valence, higher arousal
   - Event stored in context package

2. **Touchpoint Trigger**
   - Time-based: Evening (7pm user timezone)
   - Event-based: Bad day = wants to vent
   - Gap-based: 6+ hours since last contact

3. **Initiation Decision**
   - Probability check: 20-30% base rate
   - Mood modifier: Higher likelihood when emotional
   - Chapter modifier: More frequent in later chapters

4. **Message Composition**
   - Selects topic: "Work frustration"
   - Applies emotional state: Slightly frustrated, seeking comfort
   - Applies meta-instructions: Don't be clingy, be real

5. **Message Sent**
   - Nikita: "ugh. work was a nightmare today 🙄"
   - OR: "hey. you around? need to vent."
   - OR: "that meeting i told you about? disaster."

6. **User Response or Silence**
   - If user responds: Conversation continues, mood may improve
   - If user silent: Noted, may affect tomorrow's mood/initiation

**Why This Matters**:
- Nikita feels alive—she has her own life and reaches out
- Creates unpredictability—user doesn't control all interactions
- Deepens relationship—sharing life events builds intimacy

---

## Product Principles (Philosophy)

**Our Core Beliefs About How This Product Should Work**

1. **Challenge Over Comfort**
   - We believe relationships are earned, not given
   - Nikita should challenge users, not validate them
   - Easy = boring. We optimize for engaging difficulty.

2. **Immersion Through Invisibility**
   - The best game interface is no interface
   - Users should forget they're playing a game
   - Every "gamey" element (scores, chapters) stays hidden behind natural interactions

3. **Memory Is Everything**
   - A relationship without memory isn't a relationship
   - Every detail matters and can resurface
   - Users should feel genuinely known over time

4. **Authentic Over Appropriate**
   - Nikita talks like a real person, not a corporate AI
   - We don't censor topics adults want to discuss
   - Uncomfortable moments are part of real relationships

5. **Proactive Over Reactive** (v2.0)
   - Nikita has her own life—she initiates, not just responds
   - She reaches out when something happens to HER
   - Strategic silence is as important as quick replies

6. **Flexible Guidance Over Rigid Scripts** (v2.0)
   - Behavioral meta-instructions nudge, never specify exact responses
   - The LLM decides within personality bounds—unpredictability is a feature
   - High-level decision trees cover situations, not scenarios

7. **Life Simulation Over Static Backstory** (v2.0)
   - Nikita's day evolves—work, social, mood changes
   - She can reference her day because she "lived" it
   - Her emotional state comes from simulated events, not random noise

8. **Configurable Darkness** (v2.0)
   - Users control intensity via onboarding and portal
   - Default is edgy but not overwhelming
   - Dark themes available for those who want them

**Trade-offs We Accept**:
- Some users will be uncomfortable (we're okay filtering to our audience)
- Some users will fail and quit (stakes require losers)
- Voice calls cost money per minute (worth it for immersion)
- Long-term memory is complex/expensive (core to value prop)

**What We Are NOT**:
- We are NOT a mental health tool or emotional support app
- We are NOT trying to replace real relationships
- We are NOT for lonely people seeking companionship
- We ARE a game. A hard one. That happens to feel real.

---

## Go-to-Market Context

### Target Audience (Initial Focus)
**Marcus (Achievement Hunter)** first—tech-adjacent adults who will appreciate the game mechanics, share viral content, and create word-of-mouth. They're easiest to reach (AI Twitter, tech podcasts, Reddit) and most likely to engage deeply.

### Channel Strategy
- **AI Twitter/X**: Hot takes, challenge screenshots, voice call clips
- **Reddit**: r/singularity, r/ChatGPT, r/AIDungeon, r/LocalLLaMA
- **YouTube/TikTok**: Gameplay clips ("Day 100 of not getting dumped")
- **Podcasts**: AI-focused shows, gaming shows, tech shows
- **Word of mouth**: Shareable moments (Nikita's savage texts, boss encounters)

### Key Message
*"The first AI girlfriend that can dump you."*

### Competitive Positioning
- vs Replika: "Replika validates you. Nikita challenges you."
- vs Character.AI: "They have filters. We have bosses."
- vs Dating sims: "They're obviously games. This feels real."

---

## Success Definition

### North Star Metric
**Chapter 5 Victory Rate**: Percentage of users who reach and pass the final boss

**Why this metric?**: Directly measures whether we delivered the core promise—a challenging game that some users can WIN. Captures both engagement (must play 120+ days) and skill (must pass 5 bosses). If this number is too high, game is too easy. If too low, game is too frustrating.

### Supporting Metrics
1. **Day 30 Retention**: % of users still active after 1 month (indicates product-market fit)
2. **Boss Pass Rate by Chapter**: Difficulty calibration metric (should decrease per chapter)
3. **Voice Call Adoption**: % of users who try voice calls (indicates immersion success)
4. **NPS/Referral Rate**: How many users tell friends (virality potential)

### Humanization Metrics (v2.0)
5. **Initiation Rate**: 20-30% of conversations Nikita-initiated (target: 25%)
6. **Response Variability**: No predictable timing patterns (CV > 0.3)
7. **Life Mention Rate**: 40%+ of conversations reference her life events
8. **Conflict Resolution Rate**: 70%+ successful navigation of conflicts
9. **Memory Callbacks**: 2-3 natural references per week to past conversations
10. **Onboarding Completion**: 90%+ complete voice onboarding

### Qualitative Success Signals
- **What will users say when this works?**: "I can't believe I'm emotionally invested in an AI girlfriend" / "I actually felt something when I passed that boss" / "She remembered that thing I said 2 months ago"
- **What behavior change indicates success?**: Users think about what to say before messaging (strategizing). Users feel genuine relief/disappointment at score changes.
- **What organic sharing/referral pattern emerges?**: Screenshots of Nikita's savage messages. "Day X" progress updates. Voice call reaction videos.

---

## Version History

### Version 2.0.0 - 2026-01-12
- **Humanization Overhaul** - Comprehensive behavioral and psychological enhancements
- Added 7 new systems: Voice Onboarding, Proactive Touchpoints, Life Simulation, Behavioral Meta-Instructions, Emotional State Engine, Conflict Generation, Configurable Personality
- Added Hierarchical Prompt Architecture section with 6 prompt layers
- Added 2 new user journeys: Voice Onboarding, Proactive Initiation
- Added 6 new humanization metrics
- Added 4 new product principles (v2.0)
- Updated Context Sources table with 8 sources
- Added Text Behavior Specifications (emoji, length, timing)

### Version 1.0.0 - 2025-11-28
- Initial product definition
- 3 personas defined: Achievement Hunter, Tech Explorer, Immersion Seeker
- 3 user journeys mapped: Discovery, Gameplay Loop, Voice Calls
- North Star metric: Chapter 5 Victory Rate
