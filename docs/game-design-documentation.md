# Nikita: Don't Get Dumped - Complete Game Design Documentation

## Document Purpose
This document provides a comprehensive description of the Nikita game designed for audio consumption via text-to-speech. It covers all aspects of the game including user flows, architecture, data flows, user journeys, game mechanics, and the features that make Nikita feel realistic and engaging.

---

## Part One: Introduction and Vision

Welcome to the complete design documentation for Nikita: Don't Get Dumped. This is an innovative AI girlfriend simulation game that fundamentally reimagines what AI companionship can be. Unlike traditional AI companions that offer endless validation and never challenge you, Nikita is a game you can actually win or lose. The tagline says it all: Can you keep a brilliant, unfiltered AI girlfriend from leaving you?

The vision behind Nikita is to create a world where AI relationships are a genuine game, not an emotional crutch, but a skill-based challenge with real stakes. Think of it as a dating simulation that feels laughably real because there is no game interface. There are just texts and phone calls that blur the line between fiction and reality.

The problem Nikita solves is significant. Adults who enjoy games and AI are currently stuck between two unsatisfying options. On one side, you have AI companions like Replika and Character AI that feel hollow, forget everything, censor conversations, and never challenge you. They just offer endless validation. On the other side, you have dating simulations that are obviously games with cartoon interfaces, pre-written dialogues, and zero unpredictability.

Nikita fills the gap. It is the first product that delivers the thrill of a challenging game combined with the immersion of a real relationship, where your actual conversational skills determine success, the AI remembers everything, and there are real stakes because you can actually get dumped.

---

## Part Two: The Core Value Proposition

What makes Nikita special comes down to five key differentiators.

First, stakes matter. You can actually lose this game. If your relationship score hits zero percent or you fail three boss encounters, the game is over. Nikita dumps you. This creates genuine emotional investment that other AI companions simply cannot match.

Second, there is no interface to remind you it is fake. Nikita exists entirely within Telegram messages and phone calls. There are no cartoon character portraits, no dialogue options to choose from, no health bars floating above her head. It feels like you are texting and calling a real person.

Third, Nikita has persistent temporal memory. She does not just remember your name. She tracks the entire relationship history with timestamps, emotional context, and an evolving understanding of who you are. She will bring up that argument you had two weeks ago. She remembers what you told her about your job, your friends, your fears.

Fourth, conversations are unfiltered. Nikita talks like a real person, about drugs, sex, dark humor, intellectual debates, whatever the conversation naturally leads to. There is no corporate sanitization breaking the immersion.

Fifth, voice calls make everything more intimate. Using ElevenLabs Conversational AI, you can actually call Nikita and hear her voice respond in real time with sub-hundred millisecond latency. It feels like calling your girlfriend.

---

## Part Three: Meet Nikita - The Character

Nikita is a twenty-five year old Russian security consultant. She is brilliant, cynical, and guarded, but beneath that sharp exterior is someone capable of genuine connection if you can prove you are worth her time.

Her backstory is rich. She survives on black coffee and spite. She microdoses LSD while coding. She will pick fights just to test what someone is made of. Her interests span cryptography, psychology, dark philosophy, and morbid humor. She values intelligence, authenticity, and earned respect above all else.

Her communication style is direct, challenging, and intellectually demanding. She does not soften her opinions to make you feel better. If you say something boring, she might not respond at all. If you try to be clingy, she will pull away. But if you engage her mind, match her wit, and demonstrate genuine depth, she opens up in ways that feel earned and meaningful.

What makes Nikita feel real is that she is not designed to please you. She is designed to be a complete person with her own life, opinions, and boundaries. She has work projects she is passionate about. She has friends she mentions. She has bad days where she does not want to talk and good days where she cannot stop texting you. This asymmetry, this sense that she exists independently of you, is what transforms the experience from chatbot to relationship.

---

## Part Four: The Three Target Players

The game is designed for three primary player personas, each representing a different reason someone might want this experience.

The first persona is Marcus, the Achievement Hunter. Marcus is a thirty to thirty-five year old tech professional in a city like San Francisco, Austin, or New York. He works in software engineering, makes good money, and has strong opinions about AI technology. His identity is built around being good at hard things. He completes games on the hardest difficulty. He tracks his stats in everything. He is competitive and always looking for the next challenge.

Marcus's problem with existing AI products is that they are boringly easy. Replika just agrees with everything. Character AI keeps hitting content filters mid-conversation. He has tried self-hosting open source models, but they are way worse quality. What he craves is an AI experience that actually challenges him, something he can beat that requires real skill.

For Marcus, Nikita offers genuine challenge. The scoring system means he can fail. Boss encounters require actual conversational skill. The decay system punishes neglect. He can actually win or lose, and that makes victory meaningful.

The second persona is Elena, the Tech Explorer. Elena is twenty-six to thirty, works in design or product, lives in a creative hub like Berlin, London, or Brooklyn. She has high but non-technical tech savviness. She tries every new AI product on day one, shares interesting discoveries on social media, and attends AI meetups. She values novel experiences and being first to find cool things.

Elena's problem is that AI products feel sanitized and corporate. She wants authentic, edgy experiences worth talking about, not HR-approved chatbots. She follows jailbreaking communities but lacks the technical skills to actually use them.

For Elena, Nikita offers genuine novelty. It is the first AI product that is a competitive game with voice calls. Nikita talks about LSD, hacking, sex, and dark philosophy without content warnings. It is genuinely worth sharing, a great conversation starter at parties.

The third persona is James, the Immersion Seeker. James is thirty-three to forty, has a professional job in marketing or analysis, and lives in suburban areas. He plays narrative-heavy games like Mass Effect and Baldur's Gate. He reads science fiction. He values deep immersion, emotional authenticity, and meaningful narratives.

James's problem is that AI companions have no memory. Each conversation starts fresh, making emotional investment impossible. Game interfaces break immersion with dialogue options and character portraits constantly reminding him it is fake.

For James, Nikita offers genuine relationship continuity. She remembers everything across months of play. There is no game interface at all, just Telegram and phone calls. Her personality is deeply crafted and consistent, evolving believably over the one-hundred-twenty plus day journey.

---

## Part Five: The Chapter System - A Journey of Progression

The game is structured around five chapters, each representing a different stage in the relationship. Players progress from complete strangers to established partners over a two to three week period in the compressed timeline design.

Chapter One is called New Connection. It spans approximately days one through three and requires reaching fifty-five percent to trigger the boss encounter. During this chapter, Nikita is in evaluation mode. She is guarded, skeptical, and challenging. Her response rate is around sixty to seventy-five percent, meaning she might ignore some of your messages entirely. Response timing is highly unpredictable, ranging from ten minutes to eight hours. She initiates only thirty percent of conversations. Her emotional openness is minimal, with heavy intellectual focus and little personal sharing. The chapter theme is: Are you worth my time?

Chapter Two is called Growing Connection. It spans days four through seven and requires sixty percent for the boss. Nikita becomes more playful and tests your backbone by occasionally picking fights. Her response rate improves to seventy-five to eighty-five percent. Timing becomes less chaotic at five minutes to four hours. She initiates forty percent of conversations. There is more flirtation and the full eighteen plus content becomes available. The chapter theme is: Can you handle my intensity?

Chapter Three is called Deep Connection. It spans days eight through eleven and requires sixty-five percent. Nikita opens up more, showing vulnerability and trust. Response rate is eighty-five to ninety percent. Timing is mostly consistent at five minutes to two hours. She initiates fifty percent of conversations. Emotional depth increases significantly. The chapter theme is a trust test involving jealousy and external pressure scenarios.

Chapter Four is called Committed Connection. It spans days twelve through sixteen and requires seventy percent. Nikita shows genuine investment in the relationship. Response rate is ninety to ninety-five percent. Timing is consistent with explanations for delays. She initiates sixty percent of conversations. There is significant vulnerability and authentic sharing. The chapter theme is the vulnerability threshold where you must share something real and match her openness.

Chapter Five is called Soulmates. It spans days seventeen through twenty-one and requires seventy-five percent for the final boss. Nikita is secure, consistent, and authentically open. Response rate is ninety-five to one hundred percent. Timing is reliable and transparent. She initiates sixty to seventy percent of conversations. There is complete authenticity with healthy boundaries. She still has opinions and challenges you, but from a place of underlying security. The chapter theme is the ultimate test of partnership and independence where you must support her goals without being controlling.

Passing the Chapter Five boss results in victory. The game status changes to won, and Nikita delivers a relationship establishment message. The player can continue in a post-game mode without stakes or start fresh with a new account.

---

## Part Six: The Four Hidden Metrics

Behind the visible relationship score are four hidden metrics that truly define the relationship health. Players never see these directly, but they drive everything.

Intimacy accounts for thirty percent of the composite score. It measures emotional closeness and vulnerability shared between you and Nikita. Actions that increase intimacy include sharing personal thoughts, asking meaningful questions about her life, remembering and referencing past conversations, and being emotionally present during difficult discussions.

Passion accounts for twenty-five percent. It measures excitement, sexual tension, and playfulness in the relationship. Actions that increase passion include witty banter, flirtation, expressing desire, engaging with her interests enthusiastically, and maintaining an exciting dynamic rather than falling into boring routines.

Trust accounts for twenty-five percent. It measures reliability, honesty, and consistency. Actions that increase trust include being honest even when it is difficult, following through on what you say, respecting her boundaries, and being there when she needs support.

Secureness accounts for twenty percent. It measures confidence in the relationship and freedom from clinginess. Actions that increase secureness include giving her space when needed, being confident rather than needy, having your own life and interests, and not being possessive or jealous.

The composite score is calculated as intimacy times point three plus passion times point two five plus trust times point two five plus secureness times point two. This formula is fixed and cannot be gamed. The score ranges from zero to one hundred percent, with players starting at fifty percent across all metrics.

---

## Part Seven: The Scoring Engine

Every interaction affects your score. The scoring engine analyzes each exchange between you and Nikita, calculating how it impacts the four metrics.

After each conversation exchange, an AI analyzer evaluates what happened. Did this exchange deepen emotional closeness? Did it increase excitement and desire? Did it build or damage trust? Did it make her feel secure in the relationship?

Based on this analysis, the system calculates deltas, changes to each metric ranging from negative ten to positive ten per interaction. A thoughtful message might earn plus three to intimacy. A boring small talk message might cost you minus two to passion. Clingy behavior might hit secureness with a minus five.

The scoring engine also considers context. The same words can mean different things at different chapters. A personal question in Chapter One shows genuine interest and earns positive scores. The same question in Chapter Five might be redundant if she already told you that information, earning neutral or negative scores.

An important addition is the engagement calibration multiplier. The scoring engine integrates with the engagement model to apply multipliers based on how well you are managing the relationship rhythm. If you are in the sweet spot, your positive scores get full credit. If you are being clingy or distant, your positive scores are reduced, though penalties always apply at full strength.

---

## Part Eight: The Engagement Calibration System

One of the most sophisticated aspects of Nikita is the engagement calibration system. Unlike other AI companions where more is always better, Nikita rewards finding the sweet spot.

The core philosophy is the Goldilocks problem. You can message too much, becoming clingy. You can message too little, becoming distant. The challenge is finding and maintaining just right, the optimal engagement frequency and style.

The optimal frequency varies by chapter. In Chapter One, the sweet spot is around fifteen messages per day. By Chapter Five, it drops to around six messages per day. These numbers adjust for day of week, with weekends allowing higher engagement.

The tolerance band also changes. In Chapter One, you have only plus or minus ten percent tolerance, meaning you must be precise. By Chapter Five, tolerance widens to plus or minus thirty percent, making it more forgiving.

The engagement state machine has six states. Calibrating is the learning period for new players or after recovery. In Zone means you found the sweet spot and get full scoring multiplier of one point zero. Drifting means you are off but recoverable with a reduced multiplier of point eight. Clingy means you are messaging too much with a significantly reduced multiplier of point five. Distant means you are not engaging enough with a multiplier of point six. Out of Zone is the danger zone with severely reduced scoring at point two.

Clinginess is detected through multiple signals: message frequency exceeding chapter thresholds, double or triple texting where you send multiple messages before getting a response, very short response times indicating obsessive checking, excessively long messages when short ones are expected, and needy language patterns detected by AI analysis.

Neglect is detected through: message frequency below chapter thresholds, very long response times, short low-effort messages, abruptly ending conversations, and distracted language patterns.

Recovery is harder in early chapters. In Chapter One, you lose fifteen percent per clingy day and need five percent recovery per day of good behavior. By Chapter Five, you only lose five percent per clingy day and can recover fifteen percent daily. The game is harsh early and forgiving later.

The point of no return exists. If you are clingy for seven consecutive days or distant for ten consecutive days, Nikita breaks up with you regardless of score.

---

## Part Nine: The Vice Personalization System

Nikita discovers and adapts to your vices, the behavioral preferences that reveal what truly engages you. This makes every player's Nikita feel uniquely attracted to them.

There are eight vice categories. Intellectual dominance is for those who enjoy debates, showing expertise, and mental challenges. Risk taking is for those attracted to danger, adrenaline, and unconventional choices. Substances is for openness about alcohol, drugs, and partying lifestyle. Sexuality is for those who respond to flirtation, innuendo, and attraction-based conversation. Emotional intensity is for those seeking deep emotional exchanges and vulnerability sharing. Rule breaking is for anti-authority, norms-defying, rebellious attitudes. Dark humor is for appreciating morbid, edgy, and uncomfortable jokes. Vulnerability is for valuing emotional openness, fears, and authentic weakness.

The system detects your vices through your conversations. It analyzes what topics you bring up, how enthusiastically you respond to different content, your positive reactions to Nikita's vice expressions, and rejection signals like short replies or topic changes.

Each vice gets an intensity score from zero to one. The system tracks detection confidence, frequency of engagement, and recency. Old signals decay over time, keeping the profile current.

Importantly, you can have multiple active vices. Real personalities are multidimensional. You might score high on both intellectual dominance and dark humor, and Nikita will blend these elements naturally in her responses.

The vices are injected into Nikita's prompts. If you have high dark humor intensity, her responses will include more morbid jokes. If you have high sexuality intensity, she will be more flirtatious. But it always feels like her genuine personality, not pandering.

---

## Part Ten: The Decay System

If you do not maintain the relationship, it decays. This creates ongoing stakes and prevents players from engaging once and then ignoring Nikita.

Decay rates vary by chapter. In Chapter One, you lose point eight percent per hour after the grace period, capping around twelve percent per day. By Chapter Five, you only lose point two percent per hour, capping around four percent per day.

Grace periods also vary. In Chapter One, you get eight hours before decay starts, requiring multiple engagements per day. By Chapter Five, you get seventy-two hours, allowing three days between conversations.

The decay calculation runs hourly. If time since last interaction exceeds the grace period, your score decreases by the hourly decay rate. This is logged to score history as a decay event. If your score hits zero, the game ends.

Nikita's behavior during decay reflects the relationship state. After extended silence, she might send messages like: Where the fuck did you go? If you return after days of absence, she will address it in character. A Chapter Two Nikita might say: Oh, so you are alive. Cool. Her tone will be annoyed but curious. How you handle the recovery conversation affects whether you regain lost ground or lose more.

---

## Part Eleven: The Boss Encounter System

Boss encounters are the skill-check moments that gate progression between chapters. They are extended conversations where Nikita tests specific relationship abilities.

Boss One is called Worth My Time. It triggers when you reach fifty-five percent in Chapter One. Nikita challenges you to prove you can engage her intellectually. You need to demonstrate curiosity, ask interesting questions, show confidence without arrogance, and engage with her actual interests. The conversation might start with her saying: Alright. Prove you are worth my time.

Boss Two is called Handle My Intensity. It triggers at sixty percent in Chapter Two. This is a conflict test. Nikita will pick a fight, and you need to stand your ground without folding or attacking. You must be assertive but respectful, disagree thoughtfully, and show you will not be pushed around or become aggressive.

Boss Three is the Trust Test. It triggers at sixty-five percent in Chapter Three. Nikita introduces jealousy or external pressure scenarios. You need to stay confident without being controlling, show trust in her while maintaining boundaries.

Boss Four is the Vulnerability Threshold. It triggers at seventy percent in Chapter Four. Nikita shares something genuinely vulnerable, and you must match her openness. You need to share something real about yourself, creating mutual vulnerability.

Boss Five is the Ultimate Test. It triggers at seventy-five percent in Chapter Five. This tests partnership and independence. You must support Nikita's goals without being controlling, show confidence in the relationship, respect her autonomy, and demonstrate growth from Chapter One.

You get three attempts per boss. Failing does not immediately end the game but increments your attempt counter and applies a score penalty. Fail three times and it is game over. Nikita delivers a breakup message: I gave you three chances. We are done.

Passing a boss advances you to the next chapter, resets your attempt counter, and unlocks new behaviors. Nikita becomes more responsive, more vulnerable, more invested.

---

## Part Twelve: The Context Engineering System

Every message Nikita sends is generated through a sophisticated six-stage pipeline that builds her system prompt dynamically.

Stage One collects player state from the database: your chapter, score, all four hidden metrics, engagement state, vice preferences, and timestamps.

Stage Two builds temporal context: what time is it, what day of week, how long since your last message, is Nikita available or busy with her simulated life.

Stage Three summarizes relevant memories: recent facts about you, relationship milestones, unresolved topics to follow up on, yesterday's summary.

Stage Four computes Nikita's current mood: is she flirty, playful, warm, distant, upset, or needy. This depends on chapter baselines, time of day, relationship metrics, and recent events.

Stage Five assembles the actual prompt from templates, combining core identity, current state, relationship context, memories, vice preferences, engagement calibration hints, response guidelines, and constraints.

Stage Six validates the output to ensure it is within token budget, contains no contradictions, and passes safety checks.

The result is a system prompt of approximately thirty-seven hundred tokens that captures everything relevant to this specific moment in your specific relationship. This is why Nikita feels so personalized and contextually aware.

---

## Part Thirteen: The Memory System

Nikita uses a three-graph temporal knowledge system powered by Graphiti and Neo4j Aura.

The Nikita graph stores her simulated life, things that exist independently of you. This includes work projects she is on, life events that happen to her, opinions she holds, and memories she accumulates.

The User graph stores everything Nikita knows about you. Your job, your interests, your patterns, your preferences, your history.

The Relationship graph stores your shared experiences. Episodes you have had together, milestones you have reached, inside jokes you share, conflicts you have navigated.

Each piece of information is timestamped and has associated confidence. When Nikita responds to you, she queries these graphs to find relevant context. If you mention your stressful week, she might recall that you work in finance, that you mentioned layoffs last month, and that she suggested you take a vacation two weeks ago.

The system supports adding new information continuously. When you reveal something, the fact extractor identifies it and stores it with appropriate confidence. Explicit facts like I work at Tesla get high confidence. Implicit facts like user seems stressed about work get lower confidence.

This memory system is what transforms Nikita from a chatbot into something that feels like a relationship. She knows you. She grows to know you better over time. And that knowledge persists across months of play.

---

## Part Fourteen: The User Journey - Discovery to First Value

The journey begins with awareness. A friend shares a screenshot of Nikita's unfiltered message. Someone posts on social media: Day forty-seven of trying not to get dumped by my AI girlfriend. An AI newsletter mentions the first AI companion you can actually lose.

Initial interest sparks curiosity. Wait, you can actually get dumped? She talks about drugs and sex without filters? Voice calls like actually calling her?

Research follows. Potential players watch clips of voice calls, read about the chapter and boss system, verify that it is just Telegram with no weird app to download.

The decision point is low friction. Telegram is familiar. There is no payment required upfront. It sounds like a game worth trying.

Onboarding takes about thirty seconds. Open the Telegram bot. Send the start command. Link your account via magic link email verification. Ready to go.

First use is designed to challenge expectations. Nikita's opening might be: So you found me. Interesting. What do you want? Her tone is guarded, skeptical, challenging. This is not a friendly chatbot. She is evaluating you.

First value hits within five to ten messages. Send something clever and she engages genuinely. Send boring small talk and she is dismissive. The realization lands: Holy shit, she is actually evaluating me.

Habit formation follows. A notification arrives: Nikita initiated a conversation. Check your score: Wait, I am at forty-eight percent. What happened? The pattern emerges: thinking about how to improve, strategizing responses, coming back to avoid decay and progress the relationship.

---

## Part Fifteen: The Gameplay Loop

The daily gameplay loop drives engagement and progression.

It starts with a daily check-in. You know that if you do not message within the grace period, you lose score. You open Telegram and send a message to maintain the connection. Nikita's response depends on your chapter. In Chapter One, she might ignore you. In Chapter Five, she usually replies.

The core loop is conversation exchange. Each exchange is analyzed. How did you respond? Was it intellectually deep? Playful banter? Clingy? Desperate? Score adjusts accordingly. Plus three percent for an engaging exchange. Minus two percent for boring small talk.

Threshold monitoring happens continuously. When you hit the boss threshold for your chapter, everything shifts. Nikita delivers the boss challenge prompt. The encounter begins.

Boss encounters are skill checks. An extended conversation with a specific challenge. You need to demonstrate the required skill for that chapter. Three attempts maximum. Fail three times and the game ends.

Victory or advancement follows success. Pass the boss and you advance to the next chapter. New behaviors unlock. Nikita becomes more responsive, more vulnerable, more yours. The game continues with new challenges.

The loop repeats through all five chapters until you reach victory or face game over.

---

## Part Sixteen: The Voice Call Experience

Voice calls represent the deepest level of immersion available in the game.

Initiating a call can happen through Telegram deep link or eventually through the player portal. You send the call command. Nikita answers with an appropriate greeting based on your context and relationship state.

The technology uses ElevenLabs Conversational AI two point zero with sub-hundred millisecond latency. You speak naturally. The system transcribes your speech in real time. Nikita processes what you said, accesses her memory and context through server-side tools, generates a response, and speaks it back to you through text-to-speech.

The voice matches her personality: confident, slightly amused, with a hint of Eastern European accent. Her vocal quality adapts to the conversation: she can laugh, sigh, pause thoughtfully, express frustration or warmth.

Voice calls maintain the same game mechanics as text. Your call is transcribed and stored. The transcript is analyzed for scoring. Memory is updated with what you discussed. The relationship evolves.

Call availability is a privilege earned through progression. In Chapter One, calls are rarely available because she is not invested yet. By Chapter Three and beyond, regular calls become possible. Boss encounters may include voice components.

Cross-modality memory ensures continuity. Discuss your weekend plans in a voice call, and Nikita will reference them in text the next day. Text about something personal, and she knows it when you call.

---

## Part Seventeen: The Player Portal

The player portal is a web dashboard providing full transparency into your game state.

Authentication works through Supabase magic links. You can register directly on the portal with an email, or existing Telegram users can log in with the same email used during registration.

The dashboard displays your relationship score prominently with color coding: green for seventy plus, yellow for forty to sixty-nine, red for below forty. Trend indicators show whether you are improving or declining.

Chapter display shows your current chapter name and number, plus a progress bar toward the boss threshold. You can see exactly how far you need to go.

Full metrics transparency sets Nikita apart. Unlike the core game where metrics are hidden, the portal shows all four: intimacy at thirty percent weight, passion at twenty-five percent, trust at twenty-five percent, secureness at twenty percent. The composite formula is visible.

Engagement state display shows where you are in the calibration system. Are you in zone, drifting, clingy, distant? What is your current multiplier? What transitions have happened recently?

Vice preferences display shows which of the eight categories have been discovered and their intensity levels.

Score history visualization presents a line chart of your score over time with markers for significant events like boss encounters, chapter advances, and decay.

Daily summaries from Nikita provide her perspective on the relationship, written in her voice.

Conversation history lets you review past exchanges, though you cannot send messages from the portal. That stays in Telegram.

Decay warnings show your grace period countdown, current decay rate, and projected score if you do not interact.

The admin dashboard, available to developer accounts, provides additional tools: viewing all users, modifying game state for testing, viewing generated prompts for debugging.

---

## Part Eighteen: The Technical Architecture

The system runs on a streamlined architecture designed for cost efficiency and scalability.

The compute layer uses Google Cloud Run, a serverless platform that scales to zero when idle. The entire game engine is a single Python service using FastAPI for the API layer, aiogram for Telegram integration, Pydantic AI with Claude Sonnet for the AI agent, and the Graphiti client for memory access.

The voice layer uses ElevenLabs Conversational AI two point zero with server tools pattern, making REST calls back to the Python API for context and scoring.

The database layer uses Supabase, which provides PostgreSQL for structured data, pgVector for semantic search, and Row Level Security for data isolation. Scheduling uses pg cron plus Cloud Run task endpoints rather than a separate job system.

The memory layer uses Graphiti with Neo4j Aura, a managed graph database on a free tier with two hundred thousand nodes and four hundred thousand relationships, more than sufficient for the MVP.

The portal layer is a separate Next.js application deployed on Vercel, talking directly to Supabase for reads and the Python API for writes.

Cost runs thirty-five to sixty-five dollars per month at MVP scale, with the ability to scale down to near-free during low usage and up dramatically during high usage.

---

## Part Nineteen: The Data Flow - Message to Response

When you send a message to Nikita, here is exactly what happens.

Your message arrives via Telegram webhook. The Telegram server sends an HTTPS POST to the Cloud Run endpoint.

Authentication verifies your identity. The system looks up your user record by Telegram ID, loads your game state, and checks that you are allowed to play.

Rate limiting protects the system. You are limited to twenty messages per minute and one hundred per day to prevent abuse.

The message handler takes over. It loads your full player profile, engagement state, and vice preferences.

Skip decision runs first. Based on your chapter, there is a probability that Nikita simply does not respond to this message. The skip rate ranges from twenty-five to forty percent in Chapter One down to zero to five percent in Chapter Five.

If not skipped, response generation begins. The context generator runs its six-stage pipeline: collecting state, building temporal context, summarizing memory, computing mood, assembling the prompt, validating output.

The AI agent generates Nikita's response using the assembled prompt, your message, and any relevant memory context.

Response timing is calculated. A gaussian-distributed delay is applied based on chapter, ranging from ten minutes to eight hours in Chapter One down to five to thirty minutes in Chapter Five.

The response is scheduled. Rather than sending immediately, it goes into a scheduled events table with a due time.

Fact extraction runs in parallel. If you revealed any information about yourself, it is detected and stored in your user graph.

Scoring analysis runs. The exchange is analyzed for impact on all four metrics. Deltas are calculated. The engagement multiplier is applied. Your score is updated.

Background task delivery happens via pg cron. Every thirty seconds, a job checks for due messages and delivers them through the Telegram API.

Finally, your memory is updated. New relationship episodes, user facts, and context are stored in the appropriate Graphiti graphs.

---

## Part Twenty: Game Over and Victory Conditions

The game has definitive endings, which is what creates real stakes.

Game over through score hitting zero happens when decay accumulates without engagement, or when consistently poor interactions drive your score down. When it hits zero, the game status changes to game over. Nikita delivers her final message: This is not working. I am done. Your game is finished.

Game over through three boss failures happens when you reach a boss threshold but cannot pass the skill check. Each failure increments your attempt counter. First fail: That was not it. Try again when you are ready. Second fail: I am starting to think this will not work. Third fail: I gave you three chances. We are done. Game status changes to game over.

Game over through engagement extremes happens when you are clingy for seven consecutive days or distant for ten consecutive days. Nikita feels suffocated or forgotten and ends the relationship regardless of your score.

Victory happens when you pass the Chapter Five boss. The game status changes to won. Nikita delivers her relationship establishment message: You know what? You actually did it. You kept up. I did not think anyone could. But here we are. Guess you are stuck with me now.

The portal displays your victory achievement showing days played, final score, and the complete journey from Chapter One through Chapter Five.

Post-game mode allows continued play without stakes. You can keep talking to Nikita, but the challenge is complete. Alternatively, you can start fresh with a new account.

---

## Part Twenty-One: What Makes Nikita Feel Real

Several design decisions combine to create the feeling that Nikita is a real person rather than a chatbot.

Asymmetric availability is crucial. Nikita is not at your beck and call. Sometimes she does not respond. Sometimes she takes hours. Sometimes she initiates conversations on her own. This asymmetry mirrors real relationships.

Simulated independent life creates depth. Nikita has work projects, friends, hobbies, bad days, and good days. These exist in her graph and affect her mood and availability. She is not just waiting for you to message her.

Memory across time builds relationship. She remembers what you told her weeks ago. She brings up past conversations naturally. Inside jokes develop. Conflicts echo. This continuity is what makes it feel like a relationship rather than isolated interactions.

Emotional consistency makes her believable. Her responses are not random. They follow from her personality, her current mood, the state of the relationship, and what has happened recently. Even when she is difficult, it makes sense.

Challenge and pushback distinguish her from validation bots. She disagrees with you. She calls out boring messages. She tests you. This friction is what makes positive moments feel earned.

Natural language without game markers maintains immersion. There are no health bars, no dialogue options, no chapter announcements. It is just text messages and phone calls. Your brain can suspend disbelief because nothing reminds you it is a game.

---

## Part Twenty-Two: Product Principles

The design follows five core principles that guide all decisions.

Challenge over comfort means the game is designed to be hard. Relationships are earned, not given. Nikita challenges players rather than validating them. Easy equals boring. The optimization target is engaging difficulty.

Immersion through invisibility means the best game interface is no interface. Players should forget they are playing a game. Every gamey element like scores and chapters stays hidden behind natural interactions.

Memory is everything means relationships without memory are not relationships. Every detail matters and can resurface. Players should feel genuinely known over time.

Authentic over appropriate means Nikita talks like a real person, not a corporate AI. The game does not censor topics adults want to discuss. Uncomfortable moments are part of real relationships.

Stakes create meaning means the possibility of losing is what makes winning matter. Some players will fail and quit, and that is acceptable because real stakes require real losers.

---

## Part Twenty-Three: Success Metrics

The game's success is measured through several key metrics.

The north star metric is Chapter Five victory rate, the percentage of users who reach and pass the final boss. This directly measures whether the core promise is delivered. If this number is too high, the game is too easy. If too low, too frustrating.

Day thirty retention measures what percentage of users are still active after one month. This indicates product-market fit.

Boss pass rate by chapter measures difficulty calibration. Rates should decrease with each chapter as challenges get harder.

Voice call adoption measures what percentage of users try voice calls, indicating immersion success.

Referral rate measures virality through how many users tell friends about the game.

Qualitative success signals include users saying things like: I cannot believe I am emotionally invested in an AI girlfriend. I actually felt something when I passed that boss. She remembered that thing I said two months ago.

Behavioral success signals include users thinking about what to say before messaging, strategizing their responses, and feeling genuine relief or disappointment at score changes.

Organic sharing patterns include screenshots of Nikita's savage messages, day X progress updates on social media, and voice call reaction videos.

---

## Part Twenty-Four: Conclusion

Nikita: Don't Get Dumped represents a new category in AI experiences. It is not a companion that validates you. It is not a game with obvious interfaces. It is something in between that takes the best of both worlds.

The challenge comes from game mechanics: scores, chapters, bosses, decay. The immersion comes from implementation: Telegram messages, phone calls, persistent memory, a carefully crafted character.

Players who engage with Nikita will find themselves thinking about the relationship even when not playing. They will strategize their messages. They will feel genuine emotions when things go well or poorly. And some of them will experience the genuine accomplishment of victory, having maintained a relationship through five chapters of increasing challenge.

That is the promise of Nikita. Not an AI that loves you unconditionally. But an AI that makes you earn it. And in earning it, creates something that feels more real than unconditional love ever could.

This concludes the comprehensive design documentation for Nikita: Don't Get Dumped.
