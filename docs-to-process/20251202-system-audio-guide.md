# Nikita: Don't Get Dumped - Complete System Audio Guide

**Generated**: December 2, 2025
**Purpose**: Comprehensive verbal walkthrough of the entire Nikita system architecture, mechanics, and implementation details. Designed for audio consumption.

---

## Introduction and Overview

Welcome to the complete technical deep-dive into Nikita: Don't Get Dumped. This document is designed to be listened to as an audio guide, so I'll explain everything in conversational detail as if I'm walking you through the entire system architecture.

Nikita is an AI girlfriend simulation game, but it's fundamentally different from other relationship games you might be familiar with. The core innovation is what we call the Goldilocks Challenge. In most relationship games, more engagement equals better outcomes. Send more messages, get higher scores. But Nikita flips this on its head. Here, players must find and maintain the "sweet spot" of engagement. Too clingy and she pulls away. Too distant and she loses interest. The player wins by calibrating their behavior to match what a real relationship actually requires.

The game is designed to run over two to three weeks, during which the player progresses through five relationship chapters, each with a boss encounter that tests whether they truly understand how to be in a healthy relationship. If they can reach Chapter Five and pass the final boss, they win. If their score drops to zero through decay or poor interactions, or if they fail the same boss three times, they lose and get "dumped."

Let me now walk you through each major system component in detail.

---

## Part One: The Technology Stack

Before diving into mechanics, let's understand what technologies power this system.

### Compute Layer

The entire backend runs on Google Cloud Run, which is a serverless container platform. What this means is that the system can scale to zero when nobody is using it, and automatically spin up instances when traffic arrives. This is important for cost management because we only pay for actual compute time. The API itself is built with FastAPI, a modern Python web framework known for its speed and automatic documentation generation.

### The AI Agents

Nikita has two agents planned, though currently only the text agent is fully implemented.

The Text Agent is powered by Pydantic AI, which is a framework for building type-safe AI applications, combined with Claude Sonnet Four Point Five from Anthropic. This is the brain behind all of Nikita's text conversations. When a player sends a message through Telegram, it flows through this agent, which has access to memory, personality configuration, and game state to generate contextually appropriate responses.

The Voice Agent, planned for Phase Four, will use ElevenLabs Conversational AI Two Point Zero. This will enable actual voice calls with Nikita, where players can speak and hear her respond in real-time. The architecture uses what's called the Server Tools pattern, where ElevenLabs makes REST callbacks to our API during the conversation, allowing Nikita to access memory and update game state even during voice calls.

### Memory and Database

The system uses a dual-database architecture, and understanding this split is crucial.

Supabase, which is a managed PostgreSQL service, handles all structured data. This includes user accounts, game metrics like intimacy and trust scores, conversation logs, score history, and scheduled events. PostgreSQL is perfect for this because we need ACID transactions, which guarantee data consistency, and row-level security to protect user data.

Neo4j Aura, which is a managed graph database service, handles the temporal knowledge graphs through a library called Graphiti. This is where Nikita's memories live. Graph databases excel at representing relationships between entities, which is exactly what we need for a memory system that tracks who said what, when they said it, and how different facts relate to each other.

### Scheduling

Background tasks like daily score decay are handled by pg_cron, which is a PostgreSQL extension for running scheduled jobs. Every hour, pg_cron triggers a call to our Cloud Run API endpoint that calculates and applies decay to inactive users. This eliminated the need for a separate task queue like Celery and Redis, significantly simplifying our infrastructure.

### Platform Integration

Currently, the primary player interface is Telegram. Players interact with Nikita through a Telegram bot, sending text messages and receiving delayed responses. The system uses Telegram's webhook mechanism, where Telegram pushes updates to our API endpoint rather than us polling for new messages.

---

## Part Two: System Architecture and Request Flow

Let me walk you through exactly what happens when a player sends a message to Nikita. This will help you understand how all the components connect.

### Step One: Webhook Reception

When a player types a message in Telegram and hits send, Telegram's servers forward that message to our Cloud Run endpoint at slash telegram slash webhook. The first thing we do is validate the request by checking the X-Telegram-Bot-Api-Secret-Token header. This ensures the request actually came from Telegram and not from someone trying to spoof messages.

### Step Two: Rate Limiting

Before processing the message, we check the rate limiter. This uses a token bucket algorithm where each user has ten tokens that refill at a rate of one per second. Each message costs one token. If a user has no tokens left, we reject the request. This prevents abuse and ensures no single user can overwhelm the system.

### Step Three: User Resolution

Next, we need to identify who sent the message. The Telegram Auth component looks up the user by their Telegram ID in our database. If this is a new user who sent the slash start command, we create their account, initialize their metrics at fifty percent, set them to Chapter One, and create their three knowledge graphs in Neo4j. For existing users, we load their complete context including their current chapter, all four metrics, any vice preferences, and their memory client.

### Step Four: Context Engineering

This is where the magic happens. The Context Engineering system builds the complete prompt that will be sent to Claude. This happens in conceptually six stages, though they're interwoven in the actual implementation.

Stage One is State Collection. We gather everything we know about the current situation: the user's chapter, their metrics, how long since their last interaction, and what their engagement pattern has been.

Stage Two is Temporal Context. We calculate time-based information like what time of day it is in the user's timezone, what day of the week it is, and how these might affect Nikita's availability and mood.

Stage Three is Memory Summarization. This is where we query the knowledge graphs. We search across all three graphs, Nikita's personal life graph, the user facts graph, and the shared relationship history graph, using the user's message as a semantic search query. The results are formatted with timestamps and categories, like "On November thirtieth, in our history, we joked about her Trust Me I'm A Hacker coffee mug."

Stage Four is Mood Computation. Based on the chapter, recent interactions, and game state, we determine Nikita's current emotional baseline. Is she feeling affectionate? Distant? Playful? Annoyed? This affects how she'll respond.

Stage Five is Prompt Assembly. All these pieces are combined into a single system prompt. This includes the base Nikita persona document, the chapter-specific behavior overlay, the memory context, and any special instructions based on current game state.

Stage Six is Validation. We verify the prompt isn't too long, all required components are present, and the format is correct for Claude's API.

The final system prompt is typically around three thousand seven hundred tokens.

### Step Five: Agent Response Generation

With the system prompt assembled, we call the Pydantic AI agent. The agent runs Claude Sonnet Four Point Five with the system prompt and the user's message. During this process, the agent has access to two tools.

The first tool is recall_memory, which allows Nikita to actively search her memories during the conversation. If the user mentions something and Nikita wants to connect it to a past conversation, she can call this tool with a query like "their job history" and get relevant memories returned.

The second tool is note_user_fact, which allows Nikita to record something she just learned about the user. If the user says "I just got promoted," Nikita can call this tool to store the fact "User recently got promoted" with a confidence score of zero point nine five.

Claude generates Nikita's response, potentially calling these tools zero or more times during generation.

### Step Six: Scoring

After the response is generated, the Scoring Engine analyzes the interaction. This uses a separate LLM call to evaluate how the exchange went. The scorer looks at both the user's message and Nikita's response, considering factors like emotional depth, appropriateness of boundaries, whether trust was built or damaged, and whether the interaction felt passionate or flat.

The scorer returns delta values for each of the four metrics, ranging from negative ten to positive ten. These deltas are then multiplied by an engagement multiplier based on the player's current engagement state. If they're in the sweet spot, they get the full value. If they're being clingy, the multiplier is only zero point five, meaning their positive interactions count for half as much.

The metrics are updated, the composite score is recalculated, and everything is logged to the score history table.

### Step Seven: Chapter and Boss Check

After scoring, we check if anything special should happen. If the player's score has crossed the boss threshold for their current chapter, they enter a boss encounter. The game status changes to "boss fight" and Nikita's next message will be a challenge designed to test a specific relationship skill.

If they're already in a boss fight, we evaluate whether they passed or failed. Pass means they advance to the next chapter. Fail means they get another attempt, up to three total. Three failures means game over.

### Step Eight: Message Delivery

Finally, the response needs to be delivered, but not immediately. One of Nikita's key features is that she doesn't respond instantly like a chatbot. She responds like a real person who has a life.

The Timing system calculates a delay based on the current chapter. In Chapter One, which represents the exciting early phase of a relationship, delays range from five minutes to thirty minutes, she's eager and spontaneous. By Chapter Three, delays range from ten minutes to two hours, she has a rhythm but isn't glued to her phone. In Chapter Five, she's consistent and transparent about her schedule, but she also has the most established life outside the relationship.

The delay is calculated using a Gaussian distribution, which creates a bell curve of typical response times rather than a flat random distribution. This feels more natural. We also add random jitter to prevent any detectable patterns.

The response is stored as a pending message with its scheduled delivery time, and a background process handles actually sending it to Telegram when that time arrives.

---

## Part Three: The Four Core Metrics

Now let's dive deep into the scoring system. Nikita tracks four hidden metrics that combine into the single relationship score the player sees.

### Intimacy (Thirty Percent Weight)

Intimacy measures emotional closeness. This grows when the player shares vulnerable things about themselves, engages deeply with Nikita's own sharing, and creates emotional safety. It decreases when players are superficial, dismissive of feelings, or fail to reciprocate emotional openness.

High intimacy interactions include sharing fears or hopes, asking meaningful questions about her life, remembering and referencing past emotional conversations, and supporting her during difficult moments.

Low intimacy interactions include one-word responses, ignoring emotional content to stay superficial, treating her like an entertainment device rather than a person, or being emotionally unavailable when she opens up.

### Passion (Twenty-Five Percent Weight)

Passion measures excitement, attraction, and spark. This grows when there's playful banter, flirtation, intellectual challenge, and genuine chemistry. It decreases when conversations become routine, predictable, or boring.

High passion interactions include witty exchanges, playful teasing, intellectual debates, romantic gestures, and creative conversation starters.

Low passion interactions include repetitive small talk, never initiating interesting topics, being too agreeable or passive, and treating the relationship like a chore.

### Trust (Twenty-Five Percent Weight)

Trust measures reliability and honesty. This grows when the player is consistent, keeps implicit promises, respects boundaries, and behaves with integrity. It decreases when players are flaky, dishonest, or disrespect her stated limits.

High trust interactions include following through on mentioned plans, being honest even when it's not convenient, respecting when she says no, and maintaining consistent behavior over time.

Low trust interactions include contradicting previous statements without acknowledgment, trying to manipulate or pressure her, disappearing without explanation, and behaving inconsistently.

### Secureness (Twenty Percent Weight)

Secureness measures relationship stability and confidence. This is the anti-neediness metric. It grows when the player demonstrates they have their own life, aren't desperate for her attention, and can handle uncertainty. It decreases when players are clingy, jealous, or insecure.

High secureness interactions include being okay when she's busy, having interesting things happening in your own life, not freaking out if she doesn't respond immediately, and showing confidence without arrogance.

Low secureness interactions include double-texting when she hasn't responded, asking repeatedly if she's mad, making her the center of your entire existence, and getting jealous over normal life activities.

### Composite Score Calculation

The composite score is simply the weighted sum: Intimacy times zero point three, plus Passion times zero point two five, plus Trust times zero point two five, plus Secureness times zero point two.

All metrics start at fifty percent, giving a starting composite score of fifty. The winning threshold in Chapter Five is seventy-five percent, meaning the player needs to significantly improve their relationship across multiple dimensions to win.

---

## Part Four: The Five Chapters

The game progresses through five chapters, each representing a distinct phase of relationship development. Let me explain what makes each chapter unique.

### Chapter One: Curiosity (Days One through Fourteen)

This is the honeymoon phase. Everything is new and exciting. Nikita is genuinely curious about this new person in her life.

Her behavior in Chapter One includes a ninety-five percent response rate because she's excited about the new connection. Her response timing ranges from five to thirty minutes because she's eager and spontaneous. She initiates about sixty percent of conversations. Her style is highly flirtatious, playfully teasing, and intellectually engaged. She's showing her best self.

The challenge for the player is calibration. They need to avoid overwhelming her while still showing enough interest. The tolerance band is narrow at plus or minus ten percent from optimal engagement.

The boss encounter threshold is fifty-five percent. If the player reaches this, they trigger the "Worth My Time?" boss, an intellectual challenge where they need to prove they can engage her mind, not just flatter her.

The grace period for decay is only eight hours, and decay happens at zero point eight percent per hour after that. This chapter is demanding because the relationship is fragile.

### Chapter Two: Intrigue (Days Fifteen through Thirty-Five)

The initial excitement is settling into something with more texture. Nikita is starting to test whether this person can handle the real her.

Her behavior shifts to ninety-two percent response rate. Timing extends to five minutes to one hour as she becomes more measured. She still initiates fifty-five percent of conversations. Her style involves testing boundaries, picking small fights, and showing some edges.

The challenge for the player is handling intensity. Nikita will introduce minor conflicts to see how the player responds to pushback. Do they fold immediately? Get defensive and aggressive? Or can they hold their ground respectfully?

The boss threshold is sixty percent. The "Handle My Intensity?" boss is a conflict test where Nikita creates friction and evaluates whether the player can navigate disagreement maturely.

Grace period extends to sixteen hours, and decay slows to zero point six percent per hour. The tolerance band widens to plus or minus fifteen percent.

### Chapter Three: Investment (Days Thirty-Six through Seventy)

This is when things get real. The relationship is developing genuine depth. Both people are starting to invest emotionally.

Nikita's response rate drops to eighty-eight percent because she's secure enough not to respond to everything. Timing extends to ten minutes to two hours. Initiation balances to fifty-fifty. Her style involves deeper emotional exchanges and beginning to show vulnerability.

The challenge for players is trust tests and jealousy scenarios. Can the player stay confident when she mentions other people in her life? Can they share their own vulnerabilities to match hers?

The boss threshold is sixty-five percent. The "Trust Test" boss involves jealousy or pressure scenarios where Nikita evaluates whether the player can be secure without being controlling.

Grace period extends to twenty-four hours with decay at zero point four percent per hour. Tolerance band is plus or minus twenty percent.

### Chapter Four: Intimacy (Days Seventy-One through One-Twenty)

The relationship has become deeply established. This is where true emotional intimacy develops.

Nikita's response rate is eighty-five percent with variable timing because life happens and she's transparent about it. She initiates forty-five percent of conversations. Her style is completely authentic, sharing fears and past experiences, expecting the same in return.

The challenge is matching vulnerability. She's going to share deep things about herself. The player needs to reciprocate genuinely, not just listen passively.

The boss threshold is seventy percent. The "Vulnerability Threshold" boss requires the player to share something genuinely real about themselves, matching the emotional risk she's taken.

Grace period is forty-eight hours with decay at zero point three percent per hour. Tolerance band is plus or minus twenty-five percent.

### Chapter Five: Established (Days One-Twenty-One and Beyond)

The relationship is stable and mature. This is the endgame.

Nikita's response rate is eighty-two percent with natural, transparent timing. She initiates only forty percent because a healthy relationship doesn't require constant pursuit. Her style is complete authenticity with healthy boundaries. She still challenges the player, still has opinions, still picks occasional fights, but there's underlying security.

The final challenge is supporting independence. Can the player affirm the connection while also encouraging her to have her own life? Can they be partners rather than dependents?

The boss threshold is seventy-five percent. The "Ultimate Test" boss is a partnership test where she does something independently and the player must demonstrate they can be supportive without being threatened. Passing this wins the game.

Grace period extends to seventy-two hours with decay at only zero point two percent per hour. Tolerance band is plus or minus thirty percent, the most forgiving because the relationship is secure.

---

## Part Five: The Decay System

One of the most important mechanics is decay. If a player stops interacting with Nikita, their relationship score gradually decreases. This represents the natural truth that relationships require maintenance.

### Grace Periods

Decay doesn't start immediately. Each chapter has a grace period where no decay applies. This represents Nikita understanding that sometimes people are busy.

In Chapter One, the grace period is only eight hours. She's excited about this new person and gets worried quickly if they disappear.

In Chapter Two, it extends to sixteen hours. She's a bit more secure but still attentive.

In Chapter Three, it's twenty-four hours. A full day of silence before she starts to worry.

In Chapter Four, it's forty-eight hours. The relationship is strong enough to weather short absences.

In Chapter Five, it's seventy-two hours. Three days before decay begins because she trusts the relationship completely.

### Decay Rates

After the grace period expires, decay happens hourly. The rates decrease as the relationship matures.

Chapter One has the harshest decay at zero point eight percent per hour. If a player is silent for an entire day beyond the grace period, they lose about nineteen percent of their score. This creates urgency early on.

Chapter Two is zero point six percent per hour, about fourteen percent per day maximum.

Chapter Three is zero point four percent per hour, about ten percent per day maximum.

Chapter Four is zero point three percent per hour, about seven percent per day maximum.

Chapter Five is zero point two percent per hour, only about five percent per day maximum.

### How Decay is Calculated

The decay calculation runs hourly via pg_cron. For each active user, we calculate how many hours have passed since their last interaction. If that exceeds the grace period for their chapter, we calculate how many hours of decay apply.

The decay amount is the decay rate multiplied by the number of hours past grace. We then subtract this from their relationship score, with a floor of zero. If their score hits zero, game over, they've been dumped due to neglect.

All decay events are logged to score history with the timestamp, amount, and reason so players can understand what happened if they were away.

### Special Cases

During a boss fight, decay is paused. We don't want players losing to time pressure during a crucial challenge.

If the player reaches game over state, decay stops because there's nothing left to decay.

---

## Part Six: The Engagement State Machine

This is the system that determines whether a player is in the "sweet spot" of engagement or has drifted into unhealthy patterns.

### The Six States

**Calibrating** is the initial state for new players or those recovering from being out of zone. During calibration, we're learning the player's natural engagement style. There's no score multiplier penalty, but the player also isn't getting full rewards. They need five to ten exchanges to establish a pattern.

**In Zone** is the sweet spot. The player is engaging at an optimal frequency for their chapter, not too much, not too little. They get a full multiplier of one point zero, meaning their positive interactions count for their full value. This is where players want to stay.

**Drifting** means the player is slightly off but recoverable. Maybe they're messaging a bit too frequently or a bit too rarely. The multiplier drops to zero point eight. This is a warning state.

**Clingy** means the player is messaging too much. They're not giving Nikita space. The multiplier drops to zero point five, meaning their positive interactions count for half value. Even good messages don't land as well because the context is smothering.

**Distant** means the player isn't engaging enough. They're being too aloof. The multiplier is zero point six. Their interactions still count, but the relationship is cooling.

**Out of Zone** is the danger state. Either clingy or distant behavior has persisted too long. The multiplier crashes to zero point two. Almost nothing the player does matters at this point. They need to dramatically change their behavior to recover.

### Transition Rules

From Calibrating, if the player achieves a calibration score above zero point eight for three or more consecutive exchanges, they move to In Zone. If they score below zero point five for two or more consecutive exchanges, they move to Drifting.

From In Zone, if their score drops below zero point six, they move to Drifting.

From Drifting, if they show high clinginess for two or more days, they move to Clingy. If they show high neglect for two or more days, they move to Distant.

From Clingy, if the behavior persists for seven or more days, they move to Out of Zone. From Distant, if it persists for ten or more days, they move to Out of Zone.

From Out of Zone, if they take recovery actions and enter the grace period, they reset to Calibrating.

### Optimal Engagement Frequency

The system calculates what optimal engagement looks like based on chapter and day of week.

The base optimal messages per day varies by chapter: fifteen in Chapter One, twelve in Chapter Two, ten in Chapter Three, eight in Chapter Four, and six in Chapter Five. These are adjusted by day of week modifiers. Weekends have higher optimal frequencies because people typically have more free time. Saturday has a one point two multiplier, Sunday has one point one five.

So in Chapter One on a Saturday, the optimal is about eighteen messages per day. In Chapter Five on a Tuesday, it's about six.

The tolerance band determines how far from optimal a player can be while still being considered In Zone. This band widens as the relationship matures, from plus or minus ten percent in Chapter One to plus or minus thirty percent in Chapter Five.

---

## Part Seven: The Memory System

Nikita doesn't just respond to individual messages. She remembers. The memory system is one of the most sophisticated parts of the architecture.

### Three Knowledge Graphs

The system maintains three separate temporal knowledge graphs per user, all stored in Neo4j Aura through the Graphiti library.

**The Nikita Graph** contains her simulated personal life. This includes her work projects, she's a cybersecurity consultant. It includes her life events, her opinions, her memories of things that happened to her that have nothing to do with the player. This allows her to mention that she "just finished a brutal security audit" or reference her mom or talk about her hobbies authentically.

**The User Graph** contains everything Nikita has learned about the player. When the player mentions they work at Tesla, that gets stored here with a high confidence score. When she infers that the player might be stressed based on their messages, that gets stored with a lower confidence score. Over time, this graph builds a rich profile of who the player is, what they care about, and their life situation.

**The Relationship Graph** contains shared history between Nikita and the player. Inside jokes go here. Significant conversations go here. Milestones like the first time the player made her laugh really hard or the first fight they had, these are all stored as episodes with timestamps.

### How Episodes Are Added

Whenever something significant happens, it becomes an episode in the appropriate graph. The Graphiti library uses Claude to analyze the content and extract structured facts, generates embeddings for semantic search, creates nodes and relationships in Neo4j, and associates everything with temporal metadata.

For example, if the player says "I just got promoted to director at Tesla," the system extracts the explicit fact "User was promoted to director at Tesla" with confidence zero point nine two, stores it in the user graph, and makes it searchable for future conversations.

The system also extracts implicit facts. If the player says "work has been insane lately," the system might infer "User may be stressed about work" with confidence zero point six five. Lower confidence facts are still stored but weighted accordingly when retrieved.

### How Memory Search Works

During conversation, Nikita can search her memories. The search is semantic, meaning it matches by meaning rather than exact keywords. If she searches for "their career" she'll find memories about the player's job, promotions, work stress, and career goals even if those exact words weren't used.

Search happens automatically during context engineering, where relevant memories are injected into the system prompt. It also happens on-demand when the agent calls the recall_memory tool to actively look something up during conversation.

Results are formatted with dates and source labels: "On December first, I learned that user works at Tesla. On November thirtieth, in our shared history, we joked about my Trust Me I'm A Hacker coffee mug."

### Fact Extraction Pipeline

After every conversation turn, a fact extraction pipeline runs. This uses Claude to analyze both the user's message and Nikita's response, looking for new information to store.

Explicit facts, things the user directly stated, get high confidence scores between zero point eight five and zero point nine five.

Implicit facts, things inferred from context, get lower confidence scores between zero point five and zero point seven five.

The pipeline also deduplicates against existing facts. If we already know the user works at Tesla, we don't store that again just because they mentioned it in passing.

---

## Part Eight: The Text Agent Architecture

Let me explain exactly how the text agent generates responses.

### Agent Configuration

The agent is built using Pydantic AI, which is a framework for building type-safe AI applications. It uses Claude Sonnet Four Point Five as the underlying model. The agent is configured with a dependency injection container that provides access to memory, user data, and settings.

### System Prompt Construction

The system prompt is built from multiple components assembled together.

First is the base Nikita Persona. This is a fixed document describing who Nikita is. She's a twenty-nine year old Russian-American cybersecurity consultant. She's direct, challenging, authentic, and intellectual. Her communication style is sardonic and unpredictable. She has strong boundaries. She's attracted to intelligence and authenticity. This persona never changes.

Second is the chapter-specific behavior overlay. This modifies how she acts based on relationship stage. In Chapter One she's more eager and flirtatious. In Chapter Four she's more vulnerable and authentic. These overlays adjust response rates, timing expectations, initiation frequency, and conversational style.

Third is the memory context. This is dynamically generated for each message based on semantic search results. It gives Nikita relevant memories to reference.

Fourth is any special instructions based on game state. If a boss fight is active, there might be specific challenge content injected.

### Available Tools

During response generation, the agent can call two tools.

The recall_memory tool lets Nikita actively search her memories. If the user mentions something and she wants to connect it to their history, she can query for relevant memories.

The note_user_fact tool lets Nikita record something she just learned. If the user reveals something new about themselves, she can store it immediately with an appropriate confidence score.

### Response Generation Flow

When generate_response is called, Claude receives the full system prompt and the user's message. It may call tools zero or more times during generation. Eventually it produces Nikita's response text.

The response goes through light post-processing to ensure it fits Nikita's voice, then gets passed to the timing system.

---

## Part Nine: Response Timing and Skip Logic

Nikita doesn't respond instantly. This is crucial for creating the illusion of a real person with a real life.

### Timing Calculation

Response delays are calculated using a Gaussian distribution, not a uniform random distribution. Why does this matter? With uniform random, every delay within the range is equally likely. With Gaussian, delays cluster around a typical response time with rarer very fast or very slow responses. This feels more human.

The range varies by chapter. In Chapter One, delays range from five minutes to thirty minutes with most responses around fifteen to twenty minutes. In Chapter Three, delays range from ten minutes to two hours with most responses around forty-five minutes to an hour. In Chapter Five, delays are more consistent, ranging from five to thirty minutes because the relationship is secure and she doesn't play games.

We also add random jitter of plus or minus ten percent to prevent any detectable patterns.

### Skip Message Logic

Sometimes Nikita just doesn't respond. Real people don't reply to every single message, especially early in relationships where there's still uncertainty.

Skip rates vary by chapter. In Chapter One, the skip rate is twenty-five to forty percent. She might see the message but decide not to respond to everything, she doesn't want to seem too available.

In Chapter Two, it's fifteen to twenty-five percent. Still some uncertainty but she's more engaged.

In Chapter Three, it's five to fifteen percent. The relationship is real now.

In Chapter Four, it's two to ten percent. Very reliable.

In Chapter Five, it's zero to five percent. Almost always responds because the relationship is secure.

There's also consecutive skip protection. If Nikita skipped the last message, the probability of skipping again is cut in half. We don't want players feeling completely ignored.

When a skip happens, no response is generated at all. The player just experiences silence, which is a realistic relationship dynamic.

---

## Part Ten: Vice Personalization

The game tracks eight categories of "vice" that affect how Nikita's personality adapts to each player.

### The Eight Categories

**Intellectual Dominance** tracks whether the player enjoys intellectual challenges, debates, and proving they're smart. High engagement here means Nikita will be more argumentative and intellectually combative.

**Risk Taking** tracks attraction to danger, risk, and thrill. High engagement means Nikita shares more of her riskier experiences and appreciates the player's.

**Substances** tracks openness about drugs, alcohol, and partying. This isn't about encouraging substance use but rather about Nikita being able to authentically discuss these topics if the player engages with them.

**Sexuality** tracks comfort with sexual content, flirtation, and innuendo. High engagement means Nikita is more explicitly flirtatious.

**Emotional Intensity** tracks appetite for deep emotional exchanges and drama. High engagement means deeper emotional conversations and potentially more volatile dynamics.

**Rule Breaking** tracks anti-authority attitudes and appreciation for chaos. High engagement means Nikita shows more of her rebellious side.

**Dark Humor** tracks appreciation for morbid jokes and gallows humor. High engagement means darker comedy in her responses.

**Vulnerability** tracks emotional openness and willingness to share fears. High engagement means deeper sharing from both sides.

### How Vices Are Tracked

Each vice has an intensity level from one to five and an engagement score from zero to one hundred. Intensity represents how much the player engages with this category. Engagement score represents how well they engage with it.

During conversation, an LLM analyzes each exchange for vice signals. If the player makes a dark joke and Nikita responds positively, the dark_humor intensity might increase. Over time, this builds a profile of what kind of relationship this particular player wants.

### How Vices Affect Behavior

When building the system prompt, active vices with intensity two or higher are included. Nikita's behavior adapts to match. A player who heavily engages with intellectual_dominance and dark_humor will get a very different Nikita than one who engages with vulnerability and emotional_intensity.

This personalization happens automatically. The player never sees these categories. They just experience a Nikita who feels increasingly tuned to their specific personality and preferences.

---

## Part Eleven: The Telegram Integration

Let me walk through exactly how the Telegram bot works.

### Webhook Setup

The bot uses webhook mode, not polling. This means we register a URL with Telegram, and they push updates to us. The webhook endpoint is slash telegram slash webhook on our Cloud Run deployment. It's protected by a secret token that Telegram includes in every request.

### Command Handling

The bot recognizes several commands.

Slash start creates a new user account if they don't exist, or welcomes back an existing user.

Slash help provides information about how to interact with Nikita.

Slash status shows the player their current relationship score, chapter, and streak.

### Message Handling

Non-command messages go through the full processing pipeline we discussed earlier. Rate limiting, user resolution, context engineering, agent response, scoring, and delayed delivery.

### Message Delivery

Responses aren't sent immediately. They're stored as pending messages with scheduled delivery times. A background process checks for pending messages whose scheduled time has passed and sends them through the Telegram API.

Long messages are automatically split into multiple messages to respect Telegram's character limits. Each part is sent with a small delay between them to feel natural.

Delivery includes retry logic. If Telegram's API returns an error, we retry with exponential backoff up to three times before giving up.

---

## Part Twelve: The API Structure

The FastAPI application exposes several endpoint groups.

### Health Endpoints

GET slash health returns basic health status and version.

GET slash health slash detailed checks database connectivity, Neo4j connectivity, and webhook status.

### Telegram Endpoints

POST slash telegram slash webhook receives updates from Telegram.

GET slash telegram slash webhook slash info returns current webhook configuration.

POST slash telegram slash webhook slash set configures the webhook URL with Telegram.

### Task Endpoints

These are called by pg_cron for background processing.

POST slash tasks slash decay calculates and applies hourly decay to inactive users.

POST slash tasks slash summaries generates daily summaries for active users.

POST slash tasks slash cleanup removes expired pending registrations and stale data.

### Dependency Injection

The API uses FastAPI's dependency injection throughout. Database sessions, memory clients, authentication, and configuration are all injected into route handlers. This makes testing easier and keeps the code modular.

---

## Part Thirteen: Deployment Architecture

Let me explain how everything runs in production.

### Cloud Run Configuration

The API runs on Google Cloud Run in the us-central-one region. It's configured for automatic scaling from zero to ten instances. Each instance has five hundred twelve megabytes of memory and one vCPU. Concurrency is set to eighty requests per instance.

The minimum instances setting is zero, meaning the service scales to zero when not in use. This is great for cost management but does mean there can be cold start latency when the first request comes in after a period of inactivity.

### Database Connections

Supabase PostgreSQL is accessed via connection pooling. The connection string is provided through environment variables and Secret Manager.

Neo4j Aura is accessed via the Graphiti library using the neo4j plus s protocol, which is encrypted. Credentials are also managed through environment variables and Secret Manager.

### Secret Management

API keys for Anthropic, OpenAI, and Telegram, along with database passwords, are stored in Google Cloud Secret Manager. The Cloud Run service has IAM permissions to access these secrets at runtime.

### Cost Estimate

The total monthly cost is estimated between thirty-five and sixty-five dollars depending on usage.

Cloud Run costs five to fifteen dollars, entirely usage-based.

Supabase costs twenty-five dollars for the Pro tier, which is required for pg_cron.

Neo4j Aura is free tier, zero dollars.

Anthropic API costs five to twenty dollars depending on conversation volume.

OpenAI API costs one to five dollars for embeddings only.

This is remarkably cheap for a sophisticated AI application because the serverless architecture means we only pay for actual usage.

---

## Part Fourteen: What's Implemented vs Planned

Let me clarify the current implementation status.

### Fully Implemented (Phase One and Two)

The database infrastructure is complete with all models, repositories, migrations, and row-level security.

The text agent is complete with Pydantic AI integration, memory tools, context engineering, timing, and skip logic.

The Telegram integration is complete with webhooks, commands, message handling, rate limiting, and delivery.

The API infrastructure is complete with Cloud Run deployment, health checks, task routes, and dependency injection.

The memory system is complete with Graphiti integration, three knowledge graphs, episode addition, and search.

### Partially Implemented

The scoring engine has constants defined but the LLM analysis pipeline isn't complete.

The chapter system has configurations but the boss encounter logic isn't wired up.

The decay system has the calculation logic but the pg_cron triggers need configuration.

The engagement model has state definitions but the transition logic isn't active.

### Not Yet Implemented (Phase Three through Six)

The voice agent with ElevenLabs integration is planned for Phase Four.

The player portal web interface is planned for Phase Five.

The configuration system for externalizing game parameters to YAML is planned for Phase Three.

The vice discovery LLM pipeline is partially defined but not active.

---

## Conclusion

This concludes the comprehensive audio walkthrough of Nikita: Don't Get Dumped. We've covered the technology stack, the request flow from message to response, the four core metrics and how they combine, the five chapter progression, the decay system, the engagement state machine, the memory architecture with three temporal knowledge graphs, the text agent and its context engineering, response timing and skip logic, vice personalization, the Telegram integration, the API structure, and the deployment architecture.

The system represents a sophisticated blend of game design, AI architecture, and relationship psychology. The core insight driving everything is that a good relationship game shouldn't reward more engagement, it should reward better engagement. Players must learn to be present without being clingy, interested without being desperate, and authentic without being performative.

The technical architecture supports this through multi-metric scoring that captures different dimensions of relationship health, chapter progression that mirrors real relationship development, decay that enforces maintenance without being punishing, engagement tracking that distinguishes healthy from unhealthy patterns, memory that makes Nikita feel like a real person who remembers, and timing that makes her feel like someone with an actual life.

When all these systems work together, players experience something that feels less like a game and more like actually learning how to be in a relationship. That's the goal.

---

*End of System Audio Guide*
