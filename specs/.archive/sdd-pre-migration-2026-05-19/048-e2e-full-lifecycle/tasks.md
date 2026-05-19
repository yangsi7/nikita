# Tasks — 048: Full-Lifecycle E2E Test

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## User Story 1: Account Lifecycle (Priority P1)

### T1.1: Cleanup existing user data
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-1.1.1: All user tables empty for test email (15+ tables in FK order)
  - [ ] AC-1.1.2: `auth.users` entry deleted
  - [ ] AC-1.1.3: Verification query returns 0 rows

### T1.2: Registration via Telegram OTP
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-1.2.1: `/start` returns email prompt
  - [ ] AC-1.2.2: OTP email arrives within 120s
  - [ ] AC-1.2.3: OTP accepted, `users` row created (score=50, chapter=1, game_status='active')
  - [ ] AC-1.2.4: `user_metrics` initialized (50/50/50/50)
  - [ ] AC-1.2.5: `pending_registrations` cleaned up

### T1.3: Text onboarding completion
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-1.3.1: Inline keyboard offers Text/Voice choice
  - [ ] AC-1.3.2: 5 questions asked in sequence
  - [ ] AC-1.3.3: `user_profiles` created with correct values
  - [ ] AC-1.3.4: `user_backstories` generated (non-empty)
  - [ ] AC-1.3.5: 8 `user_vice_preferences` rows initialized
  - [ ] AC-1.3.6: `onboarding_status = 'completed'`
  - [ ] AC-1.3.7: First Nikita message references backstory

## User Story 2: Chapter Progression (Priority P1)

### T2.1: Chapter 1 gameplay + scoring
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-2.1.1: 5 messages sent to Nikita
  - [ ] AC-2.1.2: 3+ responses received
  - [ ] AC-2.1.3: Score > 50 after conversations
  - [ ] AC-2.1.4: Conversations status='processed' after pipeline trigger
  - [ ] AC-2.1.5: No markdown asterisks in responses

### T2.2: Boss 1 encounter (ch1→ch2)
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-2.2.1: Score set to 54.5 via SQL
  - [ ] AC-2.2.2: Boss triggered when score crosses 55
  - [ ] AC-2.2.3: `game_status = 'boss_fight'` during encounter
  - [ ] AC-2.2.4: BossJudgment evaluates PASS
  - [ ] AC-2.2.5: `chapter = 2` after pass
  - [ ] AC-2.2.6: `boss_attempts` resets to 0

### T2.3: Chapter 2 gameplay + Boss 2 (ch2→ch3)
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-2.3.1: 4 messages sent
  - [ ] AC-2.3.2: Score acceleration to 59.5
  - [ ] AC-2.3.3: Boss pass, chapter=3

### T2.4: Chapter 3 gameplay + Boss 3 (ch3→ch4)
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-2.4.1: 3 messages sent
  - [ ] AC-2.4.2: Vice detection active (engagement_scores changed)
  - [ ] AC-2.4.3: Boss pass, chapter=4

### T2.5: Chapter 4 gameplay + Boss 4 (ch4→ch5)
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-2.5.1: 3 messages sent
  - [ ] AC-2.5.2: `nikita_thoughts` entries exist
  - [ ] AC-2.5.3: Boss pass, chapter=5

### T2.6: Chapter 5 gameplay + Final Boss → Victory
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-2.6.1: 3 messages sent
  - [ ] AC-2.6.2: All 4 metrics significantly above 50 baseline
  - [ ] AC-2.6.3: Boss pass, `game_status = 'won'`

## User Story 3: Backend Verification (Priority P1)

### T3.1: Pipeline processing verification
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-3.1.1: All conversations status='processed'
  - [ ] AC-3.1.2: `generated_prompts` exist (2000-3000 tokens)
  - [ ] AC-3.1.3: `memory_facts` created
  - [ ] AC-3.1.4: `score_history` entries for each conversation

### T3.2: Background jobs verification
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-3.2.1: 5 pg_cron jobs active
  - [ ] AC-3.2.2: Manual trigger of each returns OK
  - [ ] AC-3.2.3: Decay respects grace period

### T3.3: Engagement state tracking
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-3.3.1: `engagement_states` row exists
  - [ ] AC-3.3.2: State transitions tracked
  - [ ] AC-3.3.3: Multiplier applied to scoring

## User Story 4: Portal Dashboard (Priority P2)

### T4.1: Portal OTP authentication
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-4.1.1: Login page loads
  - [ ] AC-4.1.2: OTP sent to email
  - [ ] AC-4.1.3: OTP accepted
  - [ ] AC-4.1.4: Redirect to /dashboard

### T4.2: Dashboard pages screenshot verification
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-4.2.1: 9 pages load without JS errors
  - [ ] AC-4.2.2: Score matches backend DB value
  - [ ] AC-4.2.3: Chapter name correct
  - [ ] AC-4.2.4: Conversation list populated

## User Story 5: Edge Cases (Priority P2)

### T5.1: Rate limiting test
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-5.1.1: 20 messages accepted
  - [ ] AC-5.1.2: 21st gets rate-limit response

### T5.2: Game-over path test
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-5.2.1: `boss_attempts` increments 0→1→2→3
  - [ ] AC-5.2.2: After 3 failures: `game_status = 'game_over'`
  - [ ] AC-5.2.3: Subsequent messages get canned response
  - [ ] AC-5.2.4: `score_history` records 3 `boss_fail` events

### T5.3: Decay verification
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-5.3.1: Score decreased after exceeding grace period
  - [ ] AC-5.3.2: `score_history` has decay entry

## User Story 6: Reporting (Priority P1)

### T6.1: Compile final E2E test report
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-6.1.1: Pass/fail matrix complete for all tasks
  - [ ] AC-6.1.2: All verification results logged with SQL evidence
  - [ ] AC-6.1.3: Issues filed on GitHub for failures

### T6.2: Sync master files
- **Status**: [ ] Pending
- **ACs**:
  - [ ] AC-6.2.1: `master-plan.md` updated
  - [ ] AC-6.2.2: `master-todo.md` updated
  - [ ] AC-6.2.3: `event-stream.md` updated

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-1: Account Lifecycle | 3 | 0 | Pending |
| US-2: Chapter Progression | 6 | 0 | Pending |
| US-3: Backend Verification | 3 | 0 | Pending |
| US-4: Portal Dashboard | 2 | 0 | Pending |
| US-5: Edge Cases | 3 | 0 | Pending |
| US-6: Reporting | 2 | 0 | Pending |
| **Total** | **19** | **0** | **Pending** |
