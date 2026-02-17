# E09: Portal - Admin (18 scenarios)

> Epic: E09 | User Stories: 4 | Priority: P0=3, P1=9, P2=4, P3=0
> MCP Tools: Chrome DevTools MCP, Supabase MCP, gcloud CLI
> Source files: auth.py, admin routes, portal/app/admin/

---

## US-9.1: Admin Access
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-9.1.1 - Admin login with @silent-agents.com email [P0-Critical]
  Given a user registered with email "admin@silent-agents.com"
  When the user logs in via OTP on /login
  Then the user is redirected to /admin/users (admin landing page)
  And the sidebar shows admin navigation items (Users, Pipeline, Voice, Text, Jobs, Prompts, Health)
  # Verify: auth.py:92 → ADMIN_EMAIL_DOMAIN = "@silent-agents.com"
  # Verify: Chrome DevTools → navigate post-login, check admin sidebar

Scenario: S-9.1.2 - Non-admin email rejected from admin routes [P0-Critical]
  Given a user registered with email "player@example.com" (not @silent-agents.com)
  When the user attempts to access /admin/users
  Then the user receives 403 Forbidden or is redirected to /dashboard
  And admin endpoints return 403 status
  # Verify: GET /api/v1/admin/users with player JWT → 403
  # Verify: auth.py:191 → _is_admin_email() returns false

Scenario: S-9.1.3 - Admin sees admin sidebar navigation [P1-High]
  Given a logged-in admin user
  When the admin views any admin page
  Then the sidebar contains links to: Users, Pipeline, Voice, Text, Jobs, Prompts, Health
  And each link navigates to the correct /admin/* route
  # Verify: Chrome DevTools → take_screenshot, check sidebar links

Scenario: S-9.1.4 - Admin can access player dashboard too [P2-Medium]
  Given a logged-in admin user with both admin and player data
  When the admin navigates to /dashboard
  Then the player dashboard renders with admin's game stats
  And the admin can switch between player and admin views
  # Verify: Chrome DevTools → navigate to /dashboard, verify it loads
  # Verify: GET /api/v1/portal/stats returns data for admin user_id
```

---

## US-9.2: User Management
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-9.2.1 - User list with pagination [P0-Critical]
  Given a logged-in admin user
  And the system has 50+ registered users
  When the admin navigates to /admin/users
  Then the user list shows paginated results (default page_size)
  And each row shows email, chapter, score, game_status, last_interaction_at
  # Verify: GET /api/v1/admin/users returns AdminUserListItem array
  # Verify: Supabase MCP → SELECT COUNT(*) FROM users

Scenario: S-9.2.2 - User search by email [P1-High]
  Given a logged-in admin on /admin/users
  When the admin enters "simon" in the search field
  Then the user list filters to show only users with "simon" in their email
  # Verify: GET /api/v1/admin/users?search=simon returns filtered list
  # Verify: Supabase MCP → SELECT email FROM users WHERE email ILIKE '%simon%'

Scenario: S-9.2.3 - User detail page loads all metrics [P0-Critical]
  Given a logged-in admin
  When the admin clicks on a specific user in the list
  Then /admin/users/{user_id} page loads
  And displays: chapter, game_status, relationship_score, all 4 metrics, engagement_state
  And displays: vice preferences, boss_attempts, onboarding_status
  # Verify: GET /api/v1/admin/users/{user_id} returns AdminUserDetailResponse
  # Verify: Chrome DevTools → navigate to user detail, take_screenshot

Scenario: S-9.2.4 - Engagement history chart on user detail [P2-Medium]
  Given a logged-in admin viewing /admin/users/{user_id}
  When the engagement section is visible
  Then an engagement state history timeline is displayed
  And transitions between states (IN_ZONE, CLINGY, DISTANT, etc.) are plotted
  # Verify: GET /api/v1/admin/users/{user_id}/engagement returns EngagementResponse with transitions
  # Verify: Supabase MCP → SELECT * FROM engagement_states WHERE user_id = '{user_id}' ORDER BY created_at DESC

Scenario: S-9.2.5 - Vice preferences table on user detail [P2-Medium]
  Given a logged-in admin viewing a user with 3 vice preferences
  When the vices section is visible
  Then a table shows all 3 vices with category, intensity_level, engagement_score
  # Verify: GET /api/v1/admin/users/{user_id}/vices returns list of VicePreferenceResponse
  # Verify: Supabase MCP → SELECT category, intensity_level, engagement_score FROM user_vice_preferences WHERE user_id = '{user_id}'
```

---

## US-9.3: Pipeline Monitoring
### MCP Tools: Chrome DevTools MCP, Supabase MCP, gcloud CLI

```gherkin
Scenario: S-9.3.1 - Pipeline status shows 9 stages per conversation [P0-Critical]
  Given a logged-in admin
  And a conversation that has been processed by the 9-stage pipeline
  When the admin navigates to /admin/pipeline
  Then the pipeline status view shows all 9 stages with timing data
  And each stage shows: name, status (success/error/skipped), duration_ms
  # Verify: GET /api/v1/admin/conversations/{conversation_id}/pipeline returns PipelineStatusResponse
  # Verify: 9 stages: scoring, engagement, memory, threads, thoughts, emotional, life_sim, touchpoint, prompt_builder

Scenario: S-9.3.2 - Stage failure highlighted in pipeline view [P1-High]
  Given a conversation where the memory stage failed
  When the admin views the pipeline for that conversation
  Then the memory stage is highlighted in red/error state
  And the error message is displayed (e.g., "Neo4j connection timeout")
  And subsequent stages show as skipped or completed based on error handling
  # Verify: GET /api/v1/admin/conversations/{conversation_id}/pipeline → stage.status = "error"

Scenario: S-9.3.3 - Conversation pipeline history shows processing stats [P1-High]
  Given a logged-in admin
  When the admin navigates to /admin/pipeline
  Then overall processing statistics are shown
  And includes: total_processed, avg_duration_ms, error_rate
  # Verify: GET /api/v1/admin/processing-stats returns ProcessingStatsResponse
  # Verify: GET /api/v1/admin/pipeline-health returns PipelineHealthResponse

Scenario: S-9.3.4 - Prompt viewer shows generated prompts per user [P1-High]
  Given a logged-in admin
  When the admin navigates to /admin/prompts
  Then a list of generated prompts is shown with user, platform, timestamp
  And clicking a prompt shows the full prompt text (system_prompt content)
  # Verify: GET /api/v1/admin/prompts returns GeneratedPromptsResponse
  # Verify: GET /api/v1/admin/prompts/{prompt_id} returns full prompt text

Scenario: S-9.3.5 - Processing stats dashboard shows aggregate metrics [P2-Medium]
  Given a logged-in admin
  When the admin views /admin/health
  Then system health overview shows: total_users, active_users, total_conversations
  And pipeline metrics show: success_rate, avg_processing_time
  # Verify: GET /api/v1/admin/health returns AdminHealthResponse
  # Verify: GET /api/v1/admin/stats returns AdminStatsResponse
  # Verify: GET /api/v1/admin/metrics/overview returns SystemOverviewResponse
```

---

## US-9.4: Voice & Text Monitoring
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-9.4.1 - Voice conversation list in admin [P1-High]
  Given a logged-in admin
  And the system has 5+ voice conversations
  When the admin navigates to /admin/voice
  Then a list of voice conversations is displayed
  And each entry shows: user_email, session_id, timestamp, duration, score_delta
  # Verify: GET /api/v1/admin/conversations?platform=voice returns filtered list
  # Verify: Supabase MCP → SELECT * FROM conversations WHERE platform = 'voice' ORDER BY created_at DESC LIMIT 10

Scenario: S-9.4.2 - Voice transcript viewer in admin [P1-High]
  Given a logged-in admin viewing a voice conversation
  When the admin clicks to view transcript
  Then the full transcript is displayed with user/nikita turns
  And transcript_raw is shown alongside parsed messages
  # Verify: GET /api/v1/admin/conversations/{conversation_id} → includes messages and transcript_raw
  # Verify: Chrome DevTools → navigate, check transcript display

Scenario: S-9.4.3 - Text conversation list with pipeline status [P1-High]
  Given a logged-in admin
  When the admin navigates to /admin/text
  Then text conversations are listed with pipeline processing status
  And each shows: user_email, message count, processing status (processed/pending/error)
  # Verify: GET /api/v1/admin/conversations?platform=telegram returns filtered list

Scenario: S-9.4.4 - Job monitoring shows pg_cron status [P1-High]
  Given a logged-in admin
  When the admin navigates to /admin/jobs
  Then active pg_cron jobs are listed: decay, deliver, summary, cleanup, process
  And each shows: schedule, last_run, next_run, status
  # Verify: gcloud CLI → curl backend /api/v1/tasks/* endpoints
  # Verify: Supabase MCP → SELECT * FROM cron.job ORDER BY jobid
```
