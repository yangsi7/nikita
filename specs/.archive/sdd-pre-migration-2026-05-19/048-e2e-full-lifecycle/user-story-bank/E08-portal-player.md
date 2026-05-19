# E08: Portal - Player (22 scenarios)

> Epic: E08 | User Stories: 4 | Priority: P0=4, P1=8, P2=6, P3=0
> MCP Tools: Chrome DevTools MCP, Supabase MCP
> Source files: portal.py, auth.py, portal/ (Next.js)

---

## US-8.1: Authentication
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-8.1.1 - OTP login via email succeeds [P0-Critical]
  Given a registered user with email "player@example.com"
  When the user navigates to /login
  And enters email "player@example.com" and submits
  And enters the 6-digit OTP from email
  Then the user is redirected to /dashboard
  And a Supabase session cookie is set (sb-access-token, sb-refresh-token)
  # Verify: Chrome DevTools → navigate to /login, fill form, submit
  # Verify: Supabase auth.users table has matching email
  # Verify: Cookie contains valid JWT with sub=user_id

Scenario: S-8.1.2 - Session persistence across page reloads [P1-High]
  Given a logged-in user on /dashboard
  When the page is reloaded (F5)
  Then the user remains on /dashboard (not redirected to /login)
  And the JWT is refreshed via Supabase SSR middleware
  # Verify: Chrome DevTools → navigate, reload, check URL

Scenario: S-8.1.3 - Session expiry redirects to login [P1-High]
  Given a user with an expired JWT (session cookie removed or expired)
  When the user navigates to /dashboard
  Then the user is redirected to /login with 307 status
  # Verify: Middleware intercepts, detects missing/expired session, redirects

Scenario: S-8.1.4 - Invalid OTP shows error [P1-High]
  Given a registered user on the OTP entry screen
  When the user enters an incorrect 6-digit OTP "000000"
  Then an error message is displayed (e.g., "Invalid OTP")
  And the user remains on the login page
  # Verify: Chrome DevTools → fill OTP, submit, check for error text

Scenario: S-8.1.5 - Logout clears session and redirects [P1-High]
  Given a logged-in user on /dashboard
  When the user clicks logout (or navigates to logout action)
  Then Supabase session cookies are cleared
  And the user is redirected to /login
  And subsequent navigation to /dashboard redirects to /login
  # Verify: Chrome DevTools → click logout, check cookies cleared, navigate to /dashboard
```

---

## US-8.2: Dashboard
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-8.2.1 - Score displayed correctly on dashboard [P0-Critical]
  Given a logged-in user with relationship_score=67.5
  When the user views /dashboard
  Then the score is displayed as "67.5" (or rounded per UI design)
  And the score matches GET /api/v1/portal/stats response.relationship_score
  # Verify: Supabase MCP → SELECT relationship_score FROM users WHERE id = '{user_id}'
  # Verify: Chrome DevTools → take_screenshot of /dashboard, verify score element

Scenario: S-8.2.2 - Chapter name displayed correctly [P0-Critical]
  Given a logged-in user in chapter 3
  When the user views /dashboard
  Then the chapter is displayed with its name from CHAPTER_NAMES constant
  And chapter number and name match GET /api/v1/portal/stats response
  # Verify: engine/constants.py → CHAPTER_NAMES mapping
  # Verify: Chrome DevTools → check chapter element text

Scenario: S-8.2.3 - Engagement state shown [P1-High]
  Given a logged-in user with engagement_state="IN_ZONE"
  When the user views /dashboard
  Then the engagement state badge shows "In Zone" (or localized label)
  # Verify: Supabase MCP → SELECT state FROM engagement_states WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 1

Scenario: S-8.2.4 - Mood orb renders with correct emotional state [P1-High]
  Given a logged-in user with emotional state data (arousal, valence, dominance, intimacy)
  When the user views /dashboard or /mind
  Then the mood orb component renders without crash
  And orb color/animation reflects the current emotional values
  # Verify: Chrome DevTools → take_screenshot, check for mood-orb element
  # Verify: GET /api/v1/portal/emotional-state returns arousal, valence, dominance, intimacy

Scenario: S-8.2.5 - Life events populated on mind page [P1-High]
  Given a logged-in user with life simulation events
  When the user navigates to /mind
  Then the life events timeline shows recent events
  And events include type, description, timestamp
  # Verify: GET /api/v1/portal/life-events returns events list
  # Verify: Chrome DevTools → navigate to /mind, check life-events section

Scenario: S-8.2.6 - Conversation count accurate on dashboard [P2-Medium]
  Given a logged-in user with 15 total conversations (12 text, 3 voice)
  When the user views /dashboard
  Then the conversation count shows 15 (or matches actual DB count)
  # Verify: Supabase MCP → SELECT COUNT(*) FROM conversations WHERE user_id = '{user_id}'
  # Verify: GET /api/v1/portal/stats → total_conversations
```

---

## US-8.3: Scores & History
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-8.3.1 - Score history chart renders with data points [P0-Critical]
  Given a logged-in user with 10+ score_history entries
  When the user navigates to /scores
  Then a chart is rendered showing score over time
  And each data point corresponds to a score_history entry
  # Verify: GET /api/v1/portal/score-history returns points array
  # Verify: Chrome DevTools → navigate to /scores, check chart element exists

Scenario: S-8.3.2 - Score deltas shown per conversation [P1-High]
  Given a logged-in user with score_history entries linked to conversations
  When the user navigates to /scores/detail
  Then each entry shows score_delta, event_type, and timestamp
  And entries with event_type="voice_call" and "text" are both visible
  # Verify: GET /api/v1/portal/score-history/detailed returns DetailedScorePoint list
  # Verify: Supabase MCP → SELECT score, event_type, event_details FROM score_history WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 20

Scenario: S-8.3.3 - Filter score history by date range [P2-Medium]
  Given a logged-in user with score_history spanning 30 days
  When the user applies a date filter for last 7 days on /scores
  Then only entries within the last 7 days are shown
  And chart x-axis adjusts to the filtered range
  # Verify: GET /api/v1/portal/score-history?days=7 returns filtered results

Scenario: S-8.3.4 - Filter score history by event type [P2-Medium]
  Given a logged-in user with both text and voice_call score_history entries
  When the user filters by event_type="voice_call"
  Then only voice call entries are displayed
  # Verify: GET /api/v1/portal/score-history/detailed?event_type=voice_call

Scenario: S-8.3.5 - Trajectory visualization shows trend [P2-Medium]
  Given a logged-in user with 20+ score_history entries over 2 weeks
  When the user views the trajectory section on /scores/detail
  Then a trend line or trajectory indicator is displayed
  And trend direction (up/down/stable) reflects actual score movement
  # Verify: Chrome DevTools → check trajectory visualization element
```

---

## US-8.4: Conversations & Diary
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-8.4.1 - Conversation list populated with pagination [P0-Critical]
  Given a logged-in user with 25 conversations
  When the user navigates to /conversations
  Then conversations are listed with most recent first
  And pagination controls show (page 1 of N)
  And each item shows platform (text/voice), timestamp, preview
  # Verify: GET /api/v1/portal/conversations?page=1&page_size=10 returns paginated list
  # Verify: Supabase MCP → SELECT COUNT(*) FROM conversations WHERE user_id = '{user_id}'

Scenario: S-8.4.2 - Conversation detail shows messages [P0-Critical]
  Given a logged-in user viewing /conversations
  When the user clicks on a specific conversation
  Then the user is navigated to /conversations/{id}
  And all messages in the conversation are displayed (user + nikita turns)
  And messages show role, content, and timestamp
  # Verify: GET /api/v1/portal/conversations/{conversation_id} returns messages array
  # Verify: Chrome DevTools → navigate, check message elements

Scenario: S-8.4.3 - Thread table shows open and resolved threads [P1-High]
  Given a logged-in user with conversation threads (open and resolved)
  When the user views /mind or /conversations with thread section
  Then open threads are displayed with type and content
  And resolved threads are marked differently or collapsed
  # Verify: GET /api/v1/portal/threads returns ThreadListResponse
  # Verify: Supabase MCP → SELECT * FROM conversation_threads WHERE user_id = '{user_id}' ORDER BY created_at DESC

Scenario: S-8.4.4 - Diary entries from daily summaries [P1-High]
  Given a logged-in user with daily_summaries for the past 7 days
  When the user navigates to /diary
  Then diary entries are listed by date (most recent first)
  And each entry contains Nikita's summary text (summary_text or nikita_summary_text)
  # Verify: GET /api/v1/portal/daily-summaries returns list of DailySummaryResponse
  # Verify: Supabase MCP → SELECT date, summary_text, nikita_summary_text FROM daily_summaries WHERE user_id = '{user_id}' ORDER BY date DESC

Scenario: S-8.4.5 - Diary empty for new user shows placeholder [P2-Medium]
  Given a newly registered user with zero daily_summaries
  When the user navigates to /diary
  Then an empty state is shown (e.g., "No diary entries yet")
  And no errors are thrown
  # Verify: GET /api/v1/portal/daily-summaries returns empty list
  # Verify: Chrome DevTools → navigate to /diary, check empty state

Scenario: S-8.4.6 - Thought feed displays Nikita's simulated thoughts [P1-High]
  Given a logged-in user with nikita_thoughts records
  When the user navigates to /mind
  Then the thought feed shows Nikita's inner thoughts grouped by type
  And thoughts include content and are ordered by recency
  # Verify: GET /api/v1/portal/thoughts returns ThoughtsResponse
  # Verify: Supabase MCP → SELECT content, thought_type FROM nikita_thoughts WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 20
```
