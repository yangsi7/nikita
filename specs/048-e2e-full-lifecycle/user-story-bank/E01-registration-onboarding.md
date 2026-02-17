# E01: Registration & Onboarding (28 scenarios)

> Epic: E01 | User Stories: 4 | Priority: P0=3, P1=11, P2=11, P3=3
> MCP Tools: Telegram MCP, Supabase MCP, Gmail MCP, ElevenLabs MCP
> Source files: registration_handler.py, commands.py, handoff.py, onboarding/

---

## US-1.1: New User Registration via Telegram
### MCP Tools: Telegram MCP, Supabase MCP, Gmail MCP

Scenario: S-1.1.1 - Happy path: /start for brand-new user [P0-Critical]
  Given a Telegram user who has never interacted with @Nikita_my_bot
  When the user sends "/start" to the bot
  Then the bot responds asking for an email address
  And a pending_registration record is created with otp_state="pending"
  # Verify: Supabase MCP -> SELECT * FROM pending_registrations WHERE telegram_id = {tid}
  # Verify: Telegram MCP -> last bot message contains "email"

Scenario: S-1.1.2 - Invalid email format rejected [P1-High]
  Given a user in otp_state="pending" who has been asked for email
  When the user sends "not_an_email" as their email
  Then the bot responds "Hmm, that doesn't look like a valid email. Try again?"
  And no OTP is sent
  And the user remains in otp_state="pending"
  # Verify: Telegram MCP -> last message contains "doesn't look like a valid email"
  # Verify: Gmail MCP -> no OTP email sent to "not_an_email"

Scenario: S-1.1.3 - Expired OTP rejected [P1-High]
  Given a user who received an OTP code 15 minutes ago
  When the user enters the correct OTP code after expiry
  Then the bot responds indicating the code has expired
  And the user is prompted to request a new code via /start
  # Verify: Supabase MCP -> pending_registrations.otp_state still "pending"
  # Verify: Supabase MCP -> auth.users not created for this email

Scenario: S-1.1.4 - Wrong OTP code rejected [P1-High]
  Given a user who received an OTP code via email
  When the user enters an incorrect OTP code "000000"
  Then the bot responds indicating the code is wrong
  And the user can retry with the correct code
  # Verify: Supabase MCP -> pending_registrations unchanged
  # Verify: Telegram MCP -> last message indicates incorrect code

Scenario: S-1.1.5 - Re-registration after game_over [P1-High]
  Given a user whose game_status is "game_over"
  When the user sends "/start" to the bot
  Then the bot detects the game-over state and offers a fresh start
  And old user data is cleaned up or flagged for reuse
  And a new pending_registration is created
  # Verify: Supabase MCP -> SELECT game_status FROM app_users WHERE telegram_id = {tid}
  # Verify: commands.py:106-123 handles game_over restart logic

Scenario: S-1.1.6 - OTP send failure logged with exc_info [P2-Medium]
  Given a user submits a valid email address
  When the Supabase OTP send fails with a network error
  Then the bot responds "Something went wrong sending the code. Try /start again?"
  And the error is logged with exc_info=True (not swallowed silently)
  # Verify: registration_handler.py:86-94 logs with exc_info=True (OTP-SILENT fix)
  # Verify: Telegram MCP -> message contains "Something went wrong"

Scenario: S-1.1.7 - Rate-limited OTP requests [P2-Medium]
  Given a user who has requested 5 OTP codes in the last minute
  When the user requests another OTP via /start
  Then the bot rate-limits the request
  And responds with a retry-after message
  # Verify: rate_limiter.py MAX_PER_MINUTE=20 applies to all messages
  # Verify: Supabase MCP -> no additional OTP created

---

## US-1.2: Text Onboarding Flow
### MCP Tools: Telegram MCP, Supabase MCP

Scenario: S-1.2.1 - Complete 5 onboarding questions [P0-Critical]
  Given a newly registered user with onboarding_status="in_progress"
  When the user answers all 5 onboarding questions via Telegram
  Then onboarding_status is set to "completed"
  And user profile fields (name, age, interests, etc.) are populated
  And the user receives Nikita's first in-character message
  # Verify: Supabase MCP -> SELECT onboarding_status FROM app_users WHERE id = {uid} => "completed"
  # Verify: Supabase MCP -> SELECT * FROM user_profiles WHERE user_id = {uid} => populated fields
  # Verify: Telegram MCP -> last message is Nikita's first game message (in character)

Scenario: S-1.2.2 - Skip onboarding question [P2-Medium]
  Given a user in onboarding question 3 of 5
  When the user sends "skip" or an empty response
  Then the onboarding advances to question 4
  And the skipped field is stored as null or default
  # Verify: Supabase MCP -> profile field for Q3 is null/default
  # Verify: Telegram MCP -> next question (Q4) is sent

Scenario: S-1.2.3 - Invalid answer to onboarding question [P2-Medium]
  Given a user is asked their age during onboarding
  When the user sends "abc" (non-numeric)
  Then the bot asks the question again with a hint
  And onboarding progress does not advance
  # Verify: Telegram MCP -> re-ask message with validation hint

Scenario: S-1.2.4 - Timeout between onboarding questions [P2-Medium]
  Given a user answered question 2 but has not responded in 24 hours
  When the user sends a message after the timeout
  Then onboarding resumes from question 3 (not reset)
  And the user does not lose previously saved answers
  # Verify: Supabase MCP -> onboarding_step still at 3 (not reset to 1)

Scenario: S-1.2.5 - Voice vs text onboarding choice [P1-High]
  Given a newly registered user
  When the user is presented with the onboarding mode choice
  Then "Text" option starts US-1.2 text flow
  And "Voice" option starts US-1.3 voice flow (Meta-Nikita call)
  # Verify: Telegram MCP -> choice buttons/options presented

Scenario: S-1.2.6 - Backstory generation success [P1-High]
  Given a user has completed all 5 onboarding questions
  When the backstory generation LLM call succeeds
  Then a narrative backstory is stored in the user's profile
  And Nikita's first message references backstory elements
  # Verify: Supabase MCP -> SELECT backstory FROM user_profiles WHERE user_id = {uid} => non-null
  # Verify: handoff.py social circle + pipeline bootstrap via asyncio.create_task()

Scenario: S-1.2.7 - Backstory generation timeout fallback [P1-High]
  Given a user has completed all 5 onboarding questions
  When the backstory generation exceeds Cloud Run timeout
  Then onboarding still completes (asyncio.create_task does not block)
  And a default/minimal backstory is used
  And the user still receives Nikita's first message
  # Verify: handoff.py uses asyncio.create_task() (ONBOARD-TIMEOUT fix)
  # Verify: Supabase MCP -> onboarding_status = "completed" even without backstory

---

## US-1.3: Voice Onboarding Flow
### MCP Tools: Telegram MCP, Supabase MCP, ElevenLabs MCP (if available)

Scenario: S-1.3.1 - Meta-Nikita call initiation [P1-High]
  Given a newly registered user who chose voice onboarding
  When the voice onboarding is triggered
  Then an ElevenLabs Conversational AI session is started
  And Meta-Nikita (onboarding persona) greets the user
  # Verify: Supabase MCP -> onboarding_status = "in_progress", onboarding_mode = "voice"
  # Verify: nikita/onboarding/ module handles call setup

Scenario: S-1.3.2 - Profile collection via voice [P1-High]
  Given Meta-Nikita is in an active voice onboarding call
  When the user verbally provides name, age, and interests
  Then profile fields are extracted from speech and stored
  And Meta-Nikita confirms each piece of information
  # Verify: Supabase MCP -> user_profiles fields populated from voice transcript

Scenario: S-1.3.3 - Preference configuration via voice [P2-Medium]
  Given Meta-Nikita has collected basic profile info
  When Meta-Nikita asks about communication preferences
  Then the user's preferred response style is captured
  And vice/interest hints are stored for game initialization
  # Verify: Supabase MCP -> user_vice_preferences populated

Scenario: S-1.3.4 - Voice handoff to game [P1-High]
  Given voice onboarding profile collection is complete
  When Meta-Nikita finishes the onboarding call
  Then onboarding_status is set to "completed"
  And the user receives a Telegram message from in-game Nikita
  And social circle + pipeline bootstrap run via asyncio.create_task()
  # Verify: Supabase MCP -> onboarding_status = "completed"
  # Verify: Telegram MCP -> first in-game Nikita message sent

Scenario: S-1.3.5 - Call drop mid-onboarding [P2-Medium]
  Given a voice onboarding call is in progress at question 3
  When the call drops unexpectedly (network, user hangup)
  Then partial profile data is saved
  And onboarding_status remains "in_progress"
  And user can resume via /start → choose voice again
  # Verify: Supabase MCP -> onboarding_step = 3, onboarding_status = "in_progress"

Scenario: S-1.3.6 - Incomplete profile recovery [P2-Medium]
  Given a user's voice onboarding was interrupted at step 3
  When the user starts a new voice onboarding session
  Then Meta-Nikita acknowledges previously collected data
  And resumes from step 3 (does not restart)
  # Verify: Supabase MCP -> previous answers preserved, onboarding_step = 3

Scenario: S-1.3.7 - Post-onboarding first message [P1-High]
  Given voice onboarding completes successfully
  When the handoff to game mode occurs
  Then Nikita's first in-character message is sent via Telegram
  And the message tone matches Chapter 1 (Curiosity) behavior
  And game_status is set to "active", chapter=1
  # Verify: Telegram MCP -> first game message with Ch1 tone (guarded, challenging)
  # Verify: Supabase MCP -> game_status = "active", chapter = 1

---

## US-1.4: Returning User
### MCP Tools: Telegram MCP, Supabase MCP

Scenario: S-1.4.1 - Existing active user sends /start [P0-Critical]
  Given a user with game_status="active" and onboarding_status="completed"
  When the user sends "/start" to the bot
  Then the bot recognizes them and does not restart registration
  And responds with a personalized acknowledgment
  # Verify: Supabase MCP -> no new pending_registration created
  # Verify: Telegram MCP -> message does not ask for email

Scenario: S-1.4.2 - Game-over user sends /start [P0-Critical]
  Given a user with game_status="game_over"
  When the user sends "/start" to the bot
  Then the bot offers a fresh start option
  And if accepted, user data is reset (score=50, chapter=1, boss_attempts=0)
  And a new game session begins
  # Verify: commands.py:106-123 handles game_over re-registration
  # Verify: Supabase MCP -> relationship_score = 50, chapter = 1 after reset

Scenario: S-1.4.3 - Won user sends /start [P1-High]
  Given a user with game_status="won"
  When the user sends "/start" to the bot
  Then the bot acknowledges their victory
  And offers the option to start a new game
  # Verify: commands.py:108 checks game_status in ("game_over", "won")

Scenario: S-1.4.4 - User with pending registration sends /start [P2-Medium]
  Given a user who started registration but never completed OTP
  When the user sends "/start" again
  Then the old pending_registration is replaced or updated
  And the registration flow restarts cleanly
  # Verify: Supabase MCP -> only 1 pending_registration for this telegram_id

Scenario: S-1.4.5 - Different Telegram account, same email [P2-Medium]
  Given user A registered with email user@test.com from Telegram account 111
  When Telegram account 222 tries to register with the same email
  Then the system detects the email conflict
  And prevents duplicate account creation
  # Verify: Supabase MCP -> auth.users has unique constraint on email

Scenario: S-1.4.6 - Multi-device same Telegram account [P3-Low]
  Given a user with an active game session
  When the user sends messages from Telegram web and mobile simultaneously
  Then both messages are processed (same telegram_id)
  And no race conditions cause duplicate conversations
  # Verify: Supabase MCP -> single active conversation, no duplicates

Scenario: S-1.4.7 - Account linking via portal [P2-Medium]
  Given a user with an active Telegram game
  When the user logs into the portal with the same email
  Then the portal displays their game data (score, chapter, etc.)
  And Telegram and portal share the same user record
  # Verify: Portal API -> GET /api/v1/portal/stats returns matching data
  # Verify: Supabase MCP -> same user_id for telegram and portal auth
