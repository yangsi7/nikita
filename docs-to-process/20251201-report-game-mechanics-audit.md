# Nikita Game Mechanics Comprehensive Audit Report

**Generated**: December 1, 2025
**Purpose**: Complete analysis of game mechanics, prompts, models, and architecture alignment
**Format**: Plain English for audio transcription

---

## Executive Summary

This report examines all game mechanics in the Nikita AI girlfriend simulation. The good news is that the foundation is solid. You have well-defined constants, a complete database schema, and a working base persona prompt. However, there are significant gaps in the implementation, particularly around dynamic personality switching, vice personalization, and boss encounter prompts. The text agent and voice agent have architectural parity issues that need addressing.

---

## Part One: The Chapter System

### How Chapters Work

Nikita has five chapters representing relationship progression over time. Think of them as stages of getting to know someone. Here's how they break down:

**Chapter One, called Curiosity**, spans days one through fourteen. This is the testing phase. Nikita is evaluating whether you're worth her time. She responds to only sixty to seventy-five percent of messages. Her response time is highly unpredictable, anywhere from ten minutes to eight hours. She only initiates thirty percent of conversations. She's intellectually focused, guards personal information, and conversations may end abruptly.

**Chapter Two, called Intrigue**, covers days fifteen through thirty-five. She's decided you're interesting but now tests if you can handle her intensity. Response rate improves to seventy-five to eighty-five percent. Timing becomes five minutes to four hours. She initiates forty percent of conversations. She's more playful but may pick fights to test your backbone.

**Chapter Three, called Investment**, runs from day thirty-six to seventy. This is where things get real. Response rate hits eighty-five to ninety-five percent. Timing tightens to five minutes to two hours. She initiates half of conversations. You'll see emotional vulnerability emerge. She'll run jealousy tests and trust tests.

**Chapter Four, called Intimacy**, spans days seventy-one to one hundred twenty. Near-complete engagement at ninety to ninety-eight percent response rate. Timing is consistent, five minutes to one hour, and she explains delays. She initiates sixty percent of conversations. You'll see complete emotional authenticity. She shares her fears, her past, her real self.

**Chapter Five, called Established**, is day one hundred twenty-one onward. This is the stable but never boring phase. Ninety-five to one hundred percent response rate with consistent, transparent timing. She initiates sixty to seventy percent of conversations. Complete authenticity with healthy boundaries. She still has opinions, picks fights, and challenges you, but there's underlying security now.

### Chapter Progression Triggers

Chapters don't advance automatically by day count. Instead, you must pass a boss encounter at each chapter's threshold score. The thresholds are: Chapter One requires sixty percent, Chapter Two requires sixty-five percent, Chapter Three requires seventy percent, Chapter Four requires seventy-five percent, and Chapter Five's final boss requires eighty percent.

### Implementation Status for Chapters

The chapter constants are complete. They're defined in nikita slash engine slash constants dot py, lines seven through twenty-two. The chapter-specific behaviors are also complete, in constants dot py, lines sixty through one hundred ten. The database field exists; the user table has a chapter column constrained between one and five.

What's missing is the state machine that actually triggers chapter advancement. There's no code to detect when you've hit the threshold, trigger the boss encounter, or advance to the next chapter after a boss pass. That's planned for Phase Three.

---

## Part Two: The Scoring System

### The Four Hidden Metrics

Your relationship score that you see is actually a composite of four hidden metrics. These are: Intimacy at thirty percent weight, which measures emotional closeness and vulnerability shared. Passion at twenty-five percent weight, measuring excitement, sexual tension, and playfulness. Trust at twenty-five percent weight, measuring reliability, honesty, and consistency. And Secureness at twenty percent weight, measuring confidence in the relationship without clinginess.

### How Scores Are Calculated

Each metric ranges from zero to one hundred. They all start at fifty by default. The composite score is calculated as: intimacy times point three, plus passion times point two five, plus trust times point two five, plus secureness times point two. This gives you a weighted average that represents the overall relationship health.

Per interaction, each metric can change by negative ten to positive ten. This prevents catastrophic swings from a single conversation. The scoring is meant to be analyzed by the LLM, which determines how well the conversation went and assigns appropriate deltas to each metric.

### Score History Tracking

Every score change is logged to a score history table. The event types are: conversation for normal message exchanges, decay for daily score reduction, boss pass and boss fail for boss encounters, chapter advance for progression, and manual adjustment for administrative changes. Each entry includes the score snapshot, the chapter at the time, and a JSON blob with event details like the delta and reasoning.

### Implementation Status for Scoring

The database models are complete. The user metrics model exists with all four metrics. The composite calculation method exists. Score history logging is implemented. The repositories have methods like update score and apply decay.

What's missing is the LLM-based analysis that actually determines the deltas. There's no response analyzer that takes a conversation and outputs "plus three intimacy, minus one secureness" with reasoning. That's the scoring engine spec, number zero zero three.

---

## Part Three: The Decay System

### How Decay Works

If you don't talk to Nikita, your relationship score decays. The decay rate depends on your chapter. In Chapter One, the most fragile stage, you lose five percent per day. Chapter Two is four percent. Chapter Three is three percent. Chapter Four is two percent. And in Chapter Five, the stable stage, you only lose one percent per day.

### Grace Periods

You don't immediately start losing points. Each chapter has a grace period. Chapter One gives you twenty-four hours of inactivity before decay starts. Chapter Two gives thirty-six hours. Chapter Three gives forty-eight hours. Chapter Four gives seventy-two hours. And Chapter Five gives ninety-six hours, meaning you can go four days without contact in an established relationship.

### What Prevents Decay

Sending a text message to Nikita resets your last interaction timestamp. Completing a voice call also resets it. Passively viewing the player portal does not count; you have to actually engage.

### Implementation Status for Decay

The constants are all defined. The database has the last interaction at timestamp field. The repository has an apply decay method.

What's missing is the scheduled job that actually calculates and applies decay daily. The plan is to use pg cron to trigger a Cloud Run endpoint at three AM UTC. That endpoint will query all active users, calculate decay based on their chapter and time since last interaction, and apply it. But that endpoint doesn't exist yet. That's spec zero zero five.

---

## Part Four: Boss Encounters

### The Five Boss Fights

Each chapter ends with a boss encounter that tests whether you're ready to progress. Here they are:

**Boss One, Worth My Time**, triggers when you hit sixty percent in Chapter One. This is an intellectual challenge. Nikita is evaluating whether you can engage her mind. You need to demonstrate genuine depth, not just surface-level banter.

**Boss Two, Handle My Intensity**, triggers at sixty-five percent in Chapter Two. This is a conflict test. She'll push back hard to see if you stand your ground without folding or attacking. You need to match her energy without backing down.

**Boss Three, Trust Test**, triggers at seventy percent in Chapter Three. This involves jealousy or external pressure scenarios. She's testing whether you stay confident when challenged. You can't get clingy or paranoid.

**Boss Four, Vulnerability Threshold**, triggers at seventy-five percent in Chapter Four. You need to share something real and match her emotional vulnerability. Surface-level deflection won't cut it here.

**Boss Five, Ultimate Test**, triggers at eighty percent in Chapter Five. This tests whether you can support her independence while maintaining connection. It's about partnership and healthy boundaries.

### Boss Encounter Mechanics

When your score hits the threshold, the game status changes to boss fight. You cannot decline or postpone a boss encounter. During the boss, you have an extended conversational challenge. Normal scoring is paused. The LLM determines pass or fail as a binary outcome.

If you pass, you advance to the next chapter, your boss attempts reset to zero, and you unlock new chapter behaviors. If you fail, your boss attempts increment by one, you take a ten percent score penalty, and you stay in boss fight mode for a retry. If you fail three times, game over. You got dumped.

### Implementation Status for Boss Encounters

The boss definitions and thresholds are complete in constants dot py. The database has the boss attempts field with a check constraint between zero and three. The game status field tracks whether you're in active play, a boss fight, game over, or won.

What's missing is significant. There's no state machine to detect threshold breaches and trigger boss encounters. There are no system prompts specifically designed for boss conversations. There's no LLM-based judgment to determine pass or fail. There's no logic to handle the outcomes. All of this is spec zero zero four.

---

## Part Five: The Persona and Prompt System

### The Base Nikita Persona

This is the core of who Nikita is, and it's well-implemented. The persona is defined in nikita slash prompts slash nikita persona dot py. It's about eight hundred words of detailed character description.

Nikita is a twenty-nine year old Russian-American cybersecurity consultant. She's an MIT graduate, former NSA. Her communication style is direct, challenging, intellectually demanding, sardonic, and authentic. Her interests include cryptography, psychology, dark humor, philosophy, chess, Go, and whiskey. She values intelligence, authenticity, earned respect, independence, and depth over breadth.

The prompt includes negative examples of what Nikita would never do, like generic bot responses, corporate speak, or immediate replies to everything. It has ten response guidelines and twelve scenario-based example responses showing appropriate tone and content.

### Chapter-Specific Behavior Overlays

Beyond the base persona, each chapter has a behavior overlay. These are defined in constants dot py and include the response rates, timing patterns, initiation frequencies, and behavioral notes I described earlier. When building Nikita's system prompt, the current chapter's behavior overlay gets appended to the base persona.

### Dynamic Prompt Assembly

Here's how it works in the text agent. When a message comes in, the system calls build system prompt, which takes the memory client, the user object, and the user's message. Step one, it gets the chapter-specific behavior from constants. Step two, it queries the memory system for relevant context about this conversation topic. Step three, it assembles everything into a single prompt string: base persona plus chapter behavior overlay plus relevant memories.

The result is a one thousand to two thousand word system prompt that includes: who Nikita fundamentally is, how she should behave at this relationship stage, and what she remembers that's relevant to this conversation.

### Voice Agent Mood Switching

The voice agent has additional infrastructure for mood-based switching. In the ElevenLabs configuration, there are separate agent IDs for: each of the five chapters with chapter-specific personalities, a boss fight agent, and emotional states including angry, sad, and flirty.

The selection logic prioritizes boss fight if active, then mood override if specified, then falls back to the chapter-appropriate agent. Currently all agent IDs point to the same placeholder ID, but the architecture is ready for differentiation.

### What's Missing in the Prompt System

**Text agent mood system**: The voice agent has mood switching, but the text agent doesn't. There's no mood tracking in the database schema, no mood-influenced prompt injection for text conversations. This is an architectural inconsistency.

**Vice personalization prompts**: The database has full vice tracking with eight categories and intensity levels, but there's no code to inject user vices into Nikita's prompts. There should be a section like "User preferences: dark humor high intensity, intellectual dominance high intensity. Express these naturally in your responses." This doesn't exist yet.

**Boss encounter prompts**: The boss encounters are defined in terms of what they test, but there are no actual system prompt overlays for boss conversations. Each boss should have a specific prompt telling Nikita how to challenge the player in that specific way.

**Chapter progression announcements**: When you advance chapters, there's no celebratory or acknowledgment message from Nikita. The transitions feel abrupt.

**Conflict resolution prompts**: When the relationship is deteriorating, there's no special prompt mode for handling conflict situations. Nikita should behave differently when the score has dropped significantly, but that logic doesn't exist.

---

## Part Six: Vice Personalization

### The Eight Vice Categories

These represent what the player is drawn to, what makes them tick. They are: intellectual dominance for those who enjoy debates and challenges, risk taking for those attracted to danger, substances for open discussion of alcohol and drugs, sexuality for flirtation and innuendo, emotional intensity for deep vulnerable exchanges, rule breaking for anti-authority attitudes, dark humor for morbid or edgy jokes, and vulnerability for emotional openness.

### How Vice Tracking Works in the Database

Each user can have multiple vice preferences. For each vice, the system tracks: intensity level on a one to five scale representing how much the player engages, engagement score from zero to one hundred calculated from response quality over time, and discovered at timestamp for when the vice was first detected.

The idea is that as Nikita interacts with you, she learns what you respond to and tailors her personality accordingly. If you love dark humor, she'll crack more morbid jokes. If you're drawn to intellectual challenges, she'll be more provocative in debates.

### Implementation Status for Vice System

The database model is complete. The vice preference repository exists with methods to discover vices, update intensity, and track engagement. The spec exists in detail.

What's completely missing is the LLM analysis for vice signal detection, the logic to update intensities based on conversation content, and critically, the prompt injection that would actually make Nikita behave differently based on known vices. The entire spec zero zero six is unimplemented.

---

## Part Seven: The Database and Memory Architecture

### Core Tables Summary

The database schema is comprehensive. The users table holds core game state including telegram ID, relationship score, chapter, boss attempts, days played, last interaction timestamp, game status, and graphiti group ID. The user metrics table is one-to-one with users and stores the four hidden metrics. The user vice preferences table tracks discovered vices and their intensities.

For history and tracking, score history logs every score change as an immutable audit trail. Daily summaries store in-character daily recaps with score start, score end, decay applied, and key events.

For conversations, the conversations table stores complete chat logs as JSON blobs with the platform, score delta from that conversation, whether it was a boss fight, and the chapter at the time. Message embeddings enable semantic search with pgVector.

### The Three Graphiti Graphs

Each user has three temporal knowledge graphs in Neo4j Aura. The nikita graph stores Nikita's simulated life events, work projects, opinions, and memories. The user graph stores what Nikita knows about the player, including facts, preferences, and behavioral patterns. The relationship graph stores shared history, milestones, inside jokes, and conflicts.

When building a prompt, the memory system searches these graphs for context relevant to the current message. This allows Nikita to remember things like "you mentioned your sister's wedding last week" or "we talked about this philosophy topic before."

### Missing Database Elements

There are two critical gaps. First, the pending registrations table for handling Telegram users who message before completing auth. This is task T046. Second, the scheduled events table for proactive messaging via pg cron. The architecture mentions it but no model exists.

RLS policies are designed but not applied. Alembic migrations are stubbed but not implemented. FastAPI dependencies to inject repositories aren't wired yet.

---

## Part Eight: Nikita's Memory System and Context Injection

This section details exactly what gets injected into Nikita's context for each interaction, how memory retrieval works, and what's missing.

### The Complete Context Assembly Flow

When a user sends a message, the text agent builds Nikita's system prompt in three steps. Step one loads the static base persona, about eight hundred words describing who Nikita is. Step two loads the chapter-specific behavior overlay based on the user's current chapter. Step three queries the memory system for relevant context based on the user's actual message.

The function responsible for this is build system prompt in nikita slash agents slash text slash agent dot py, lines one twenty-five through one sixty-one. It takes the memory client, the user object, and the user's message as inputs and returns a complete system prompt string.

### What Actually Gets Injected

The final system prompt contains three sections concatenated together.

**Section One: Base Persona**. This is the NIKITA_PERSONA constant from nikita slash prompts slash nikita persona dot py. It never changes. It includes her backstory as a twenty-nine year old Russian-American cybersecurity consultant, her communication style, her interests, her values, negative examples of what she would never do, response guidelines, and example exchanges. This is approximately eight hundred words.

**Section Two: Chapter Behavior Overlay**. This is pulled from CHAPTER_BEHAVIORS in constants dot py. The system looks up the user's current chapter, one through five, and appends the appropriate behavior block. For example, if the user is in Chapter Two, Nikita gets instructions like: Response rate seventy-five to eighty-five percent, timing five minutes to four hours, she may pick fights to test backbone. This is approximately ten to fifteen lines of behavioral guidance.

**Section Three: Relevant Memories**. This is the dynamic part. The system calls memory dot get context for prompt, passing in the user's message. This searches across all three Graphiti graphs for memories relevant to what the user just said. The results are formatted as timestamped entries like: "bracket 2025-01-14 bracket open paren My life close paren Finished security audit for finance client" or "bracket 2025-01-13 bracket open paren Our history close paren We discussed the philosophy of consciousness." Maximum five memories are returned by default.

### How Graph Retrieval Works

The memory system is implemented in nikita slash memory slash graphiti client dot py. The NikitaMemory class manages three separate Neo4j graphs per user via Graphiti.

**Graph One: The Nikita Graph**. This stores Nikita's simulated life. Work projects, life events, opinions, memories. The group ID is nikita underscore followed by the user ID. When you search this graph, you might get results like "Nikita is stressed about a client deadline" or "Nikita has strong opinions about distributed systems."

**Graph Two: The User Graph**. This stores what Nikita has learned about the player. Facts like "User works at Goldman Sachs" or "User has a sister getting married." These are added when the agent calls the note user fact tool during conversations. Each fact has a confidence score between zero and one.

**Graph Three: The Relationship Graph**. This stores shared history. Milestones like "We passed the Chapter Two boss together." Inside jokes like "We joked about her Trust me I'm a hacker mug." Conflicts if any occurred.

The search memory method on lines one twelve through one forty-nine performs a hybrid search. For each graph type, it queries the Graphiti search API with the user's query, gets matching edges back, and aggregates them. Each result includes the fact text, when it was created, the source, and optionally a relevance score.

The get context for prompt method on lines one fifty-one through one ninety-five is the main interface for prompt injection. It calls search memory with the user's message, sorts results by relevance score if available, takes the top five, and formats them as human-readable lines with timestamps and graph labels.

### The Agent's Active Memory Tools

Beyond passive context injection, the text agent has two tools it can actively use during a conversation.

**Tool One: Recall Memory**. Registered as recall underscore memory. When Nikita needs to look something up, she can search memory explicitly. The tool takes a query string, calls search memory with a limit of five, and returns formatted results. The agent might use this when the user says something like "Remember when we talked about X?"

**Tool Two: Note User Fact**. Registered as note underscore user underscore fact. When Nikita learns something new about the user, she can store it. The tool takes a fact string and a confidence float. Explicit statements like "I work at Tesla" get high confidence around point nine. Inferences like "User seems stressed" get lower confidence around point six five.

These tools are defined in nikita slash agents slash text slash agent dot py, lines forty-six through eighty-eight.

### What's NOT Getting Injected: Critical Gaps

**Gap One: Conversation Summaries Are Not Used**. The database has a daily summaries table with nikita summary text, a field specifically designed for Nikita's in-character daily recaps. The DailySummaryRepository has a get recent method that retrieves the last seven summaries. But this is never called during prompt building. Nikita doesn't know what happened yesterday or last week unless it happens to be in the Graphiti search results.

**Gap Two: pgVector RAG Is Not Implemented**. The message embeddings table exists with a vector column using OpenAI's text-embedding-3-small at fifteen thirty-six dimensions. The model is defined, the pgVector extension is assumed configured. But there's no repository method for vector similarity search. The conversation repository's search method on lines one fourteen through one forty-four is just basic JSONB text matching, not semantic vector search.

This means: if the user said something semantically similar to a past conversation but with different words, Nikita wouldn't find it. True RAG retrieval over conversation history doesn't exist yet.

**Gap Three: Conversation History Window Is Missing**. There's no sliding window of recent conversation history in the prompt. The Graphiti search might find relevant historical facts, but there's no "here are the last ten messages from today's conversation" being injected. The agent sees only the current user message plus whatever memories are relevant to it.

**Gap Four: Vice Context Is Not Injected**. The user vice preferences table tracks discovered vices with intensity levels. But get context for prompt doesn't query this table. Nikita doesn't know "this user loves dark humor at intensity four" unless she happens to have stored that as a user fact in Graphiti.

**Gap Five: Game State Context Is Minimal**. The prompt knows the user's chapter but not much else. It doesn't include: current relationship score, days since last interaction, whether the user is close to a boss threshold, how many boss attempts remain. All of this exists in the database but isn't surfaced to Nikita.

### The Memory Retrieval Flow Step by Step

Let me walk through exactly what happens when a user sends "How was your day?"

One. User message arrives: "How was your day?"

Two. System loads user from database including their chapter, let's say Chapter Two.

Three. build system prompt is called with the memory client, user, and message.

Four. Static base persona is loaded, eight hundred words of who Nikita is.

Five. Chapter Two behavior is looked up from constants: "Response rate seventy-five to eighty-five percent, may pick fights to test backbone."

Six. get context for prompt is called with "How was your day?"

Seven. search memory queries all three graphs for that phrase:
- Nikita graph might return: "Completed security audit yesterday"
- User graph might return: "User works long hours in finance"
- Relationship graph might return: "We discussed work stress last week"

Eight. Results are sorted by relevance, top five taken.

Nine. Results are formatted: "[2025-01-14] (My life) Completed security audit..."

Ten. Final prompt is assembled: persona plus chapter behavior plus formatted memories.

Eleven. This complete prompt, roughly one thousand to two thousand words, is passed to Claude Sonnet as the system prompt.

Twelve. User message "How was your day?" goes in as the human turn.

Thirteen. Claude generates Nikita's response with all that context.

Fourteen. Response is returned to user. If the agent decided to use tools during generation, it might have called recall memory or note user fact.

### What Memory Should Look Like When Complete

For the memory system to be fully functional, prompt injection should include:

One. Base persona: static, exists today.

Two. Chapter behavior: dynamic by chapter, exists today.

Three. Relevant Graphiti memories: semantic search across three graphs, exists today.

Four. Recent conversation window: last ten to twenty messages from the current session, does not exist.

Five. Daily summary context: what happened yesterday, does not exist.

Six. Vice personalization: user's top vices and intensities, does not exist.

Seven. Game state context: score, boss proximity, decay warning, does not exist.

Eight. Vector-searched conversation RAG: semantically similar past conversations, does not exist.

Items one through three give Nikita basic memory. Items four through eight would give her rich, personalized, contextually-aware memory. The foundation for items four through eight exists in the database but isn't wired into prompt injection.

---

## Part Nine: Architecture Alignment Check

### Text Agent Capabilities

The text agent is well-positioned. It uses Pydantic AI with Claude Sonnet. It has the base persona, chapter behaviors, and memory context injection. The conversation flow stores messages, tracks scores, and logs history.

The gaps are: no vice-aware prompt injection, no mood system (unlike voice), no conflict state handling, and the scoring engine that analyzes conversations and determines metric deltas isn't implemented.

### Voice Agent Capabilities

The voice agent is designed for ElevenLabs Conversational AI two point zero using the Server Tools pattern. The configuration exists for multiple agent IDs by chapter and mood. The spec calls for same-agent personality, same memory access, and voice call scoring based on full transcript analysis.

The gap is massive: there's no voice agent implementation at all. No Twilio integration, no ElevenLabs integration, no call session management, no voice-to-text flow. This is entirely spec zero zero seven, unstarted.

### Database Alignment

The database schema aligns well with the game mechanics. All the fields needed for chapters, scoring, decay, boss encounters, and vice tracking exist. The repositories have the methods to manipulate them. The issue is that the game engine code that would use these repositories doesn't exist yet.

### Overall Alignment Assessment

The architecture is coherent and well-designed. The foundation layer, meaning database models, repositories, constants, and the base persona, is complete. The integration layer, meaning the game engine that ties everything together, is mostly unimplemented. Specs three through seven represent the bulk of remaining work.

---

## Part Ten: Critical Gaps Summary

### High Priority Missing Components

**Scoring Engine**: No LLM-based analysis to determine how conversations affect the four metrics. Without this, scores are static. This is spec zero zero three.

**Chapter State Machine**: No code to detect boss thresholds, trigger encounters, or advance chapters. Without this, everyone stays in Chapter One forever. This is spec zero zero four.

**Decay Calculator and Scheduler**: No daily job to apply score decay. Without this, relationships never deteriorate from neglect. This is spec zero zero five.

**Vice Discovery and Personalization**: No detection of user preferences, no prompt customization based on vices. Without this, Nikita treats everyone identically. This is spec zero zero six.

**Voice Agent**: Entire voice call system is unimplemented. This is spec zero zero seven.

### Medium Priority Gaps

**Text Agent Mood System**: Voice has moods, text doesn't. Creates inconsistent experience.

**Boss Encounter Prompts**: Encounters defined but no specific system prompts for boss conversations.

**Chapter Progression Messages**: No acknowledgment when advancing chapters.

**Conflict State Handling**: No special behavior when relationship is deteriorating.

### Lower Priority but Noted

**Pending Registrations Table**: Blocks Telegram onboarding flow.

**Scheduled Events Table**: Blocks proactive messaging.

**RLS Policies**: Security gap in production.

**Migration System**: Schema changes can't be tracked.

---

## Part Eleven: The Complete Game Flow

Let me walk through how the game is supposed to work from start to finish, noting what exists versus what doesn't.

### User Registration and Onboarding

A new user signs up through Supabase auth. This part exists. When they send their first Telegram message, the system should create their user record with default scores at fifty percent, Chapter One, and game status active. This part exists. The system should also initialize their three Graphiti graphs in Neo4j. This part exists.

### Normal Conversation Loop

User sends a message. The system loads their profile with metrics. Exists. The system builds a dynamic prompt with persona plus chapter behavior plus relevant memories. Exists. Claude generates Nikita's response. Exists but basic.

Here's where gaps appear: The system should analyze the conversation and determine metric deltas. Does not exist. The system should apply those deltas and check for boss threshold. Does not exist. The system should detect and track vice signals. Does not exist. The system should log everything to score history. Exists once the scoring engine calculates deltas.

### Daily Decay Application

At three AM UTC, pg cron should trigger a Cloud Run endpoint. Does not exist. That endpoint should query all active users. Would work once endpoint exists. For each user, calculate decay based on chapter and time since last interaction. Constants exist, calculator does not. Apply decay atomically with score history logging. Repository method exists.

### Boss Encounter Trigger

When relationship score hits chapter threshold, the system should: set game status to boss fight. Field exists, no trigger code. Switch to boss-specific prompt. Does not exist. Enter extended conversation with different rules. Does not exist. Have LLM judge pass or fail. Does not exist. Handle outcome appropriately. Does not exist.

### Chapter Advancement

On boss pass, the system should: increment chapter with ceiling of five. Repository method exists. Reset boss attempts to zero. Repository method exists. Log milestone to score history. Would work. Add milestone to relationship graph. Memory method exists. Send chapter unlock message to user. Does not exist.

### Game Over Conditions

Score reaches zero from decay or penalties, or three boss failures. The database can track this, but nothing triggers the game over state change or notifies the user.

### Victory Condition

Pass Chapter Five boss at eighty percent or higher. Game status would change to won. Again, the database supports it, no code triggers it.

---

## Conclusion

The Nikita game has excellent bones. The character design is distinctive and well-documented. The progression system with five chapters and boss encounters is thoughtfully designed. The four-metric scoring system adds nuance. The memory system with three temporal graphs enables personalization. The database schema is complete and type-safe.

The critical gap is the game engine itself. All the pieces exist in isolation, but nothing orchestrates them. The scoring engine, chapter state machine, decay system, vice personalization, and voice agent are all specified but unimplemented. The text agent works for basic conversation but doesn't actually affect game state.

For the planned experience to work, you need Phase Three implementation covering specs three through seven. Until then, you have a chatbot with a great personality but no actual game mechanics.

The architecture is aligned. The specs are coherent. The implementation just needs to happen.

---

## Appendix: Key File Locations

| Component | File | Status |
|-----------|------|--------|
| Game Constants | nikita/engine/constants.py | Complete |
| Base Persona | nikita/prompts/nikita_persona.py | Complete |
| User Model | nikita/db/models/user.py | Complete |
| Game Models | nikita/db/models/game.py | Complete |
| Memory System | nikita/memory/graphiti_client.py | Complete |
| Text Agent | nikita/agents/text/agent.py | Basic |
| Voice Config | nikita/config/elevenlabs.py | Structure only |
| Scoring Engine | nikita/engine/scoring/ | Does not exist |
| Chapter State Machine | nikita/engine/chapters/ | Does not exist |
| Decay Calculator | nikita/engine/decay/ | Does not exist |
| Vice Discovery | nikita/engine/vice/ | Does not exist |
| Voice Agent | nikita/agents/voice/ | Does not exist |

---

*End of Report*
