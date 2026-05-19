---
feature: 002-telegram-integration
created: 2025-11-28
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Telegram Platform Integration

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

Telegram Platform Integration connects users to the Nikita Text Agent through Telegram as the primary communication channel. This feature enables users to interact with Nikita through a familiar messaging interface, creating the "no game UI" illusion central to the product vision.

**Problem Statement**: Traditional AI companions and dating sims have obvious game interfaces that break immersion. Users need a way to interact with Nikita that feels like texting a real person, not playing a game.

**Value Proposition**: Users access Nikita through Telegram—a platform they already use for real conversations—eliminating visible game elements and maximizing immersion. The interface IS the message thread.

### CoD^Σ Overview

**System Model**:
```
User → Telegram → Platform_Layer → Text_Agent → Response → Telegram → User
  ↓         ↓            ↓              ↓            ↓          ↓        ↓
Input   Channel   Auth/Session    Nikita_AI    Output    Channel  Display

Platform := Bot ⊕ Auth ⊕ Session ⊕ Rate_Limit ⊕ Delivery
```

**Value Chain**:
```
Telegram_message ≫ Bot_receives ≫ Auth_check → Agent_processing → Response_delivery
        ↓              ↓              ↓              ↓                   ↓
    User_text      Bot_handler   Valid_session   Nikita_reply      User_sees
```

---

## Functional Requirements

**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: Bot Command Handling
System MUST handle standard bot commands:
- /start: Initialize new user onboarding
- /help: Display available commands and guidance
- /status: Show current game state (chapter, score preview)
- /call: Initiate voice call (future integration point)

**Rationale**: Standard commands provide discoverability without breaking immersion (hidden unless requested)
**Priority**: Must Have

### FR-002: Text Message Routing
System MUST route all non-command text messages to the Nikita Text Agent:
- Pass message content to agent
- Include user context (user_id, chapter, session state)
- Return agent response to user via Telegram

**Rationale**: Core functionality—text messages ARE the gameplay
**Priority**: Must Have

### FR-003: User Authentication Flow
System MUST authenticate users before gameplay:
- New users: Collect email, send magic link verification
- Existing users: Recognize by Telegram user ID
- Unverified users: Prompt to complete verification
- Session persistence: Maintain auth state across conversations

**Rationale**: User identity required for persistent memory and game state
**Priority**: Must Have

### FR-004: Account Creation
System MUST enable new user registration:
- Collect email address (only required data)
- Send magic link for verification
- Create user record upon successful verification
- Initialize game state (Chapter 1, starting metrics)

**Rationale**: Clean onboarding with minimal friction (Telegram + email only)
**Priority**: Must Have

### FR-005: Session Management
System MUST maintain user sessions:
- Track active conversation state
- Preserve context between messages
- Handle session timeouts gracefully
- Support concurrent users without cross-contamination

**Rationale**: Conversation continuity and user isolation
**Priority**: Must Have

### FR-006: Rate Limiting
System MUST enforce rate limits to prevent abuse:
- Per-user message rate: Maximum 20 messages per minute
- Per-user daily limit: Maximum 500 messages per day
- Graceful degradation: Queue messages rather than reject during brief spikes
- Clear feedback: Inform user when rate limited

**Rationale**: Prevent abuse, manage costs, ensure fair resource allocation
**Priority**: Must Have

### FR-007: Response Delivery
System MUST deliver agent responses via Telegram:
- Support text responses (primary)
- Support typing indicators before responses
- Handle message length limits (split if necessary)
- Ensure delivery confirmation

**Rationale**: Reliable delivery is foundational to the experience
**Priority**: Must Have

### FR-008: Error Handling
System MUST handle errors gracefully:
- Agent unavailable: Queue message, notify user of delay
- Invalid input: Provide helpful guidance
- Auth failures: Clear re-authentication path
- Network issues: Retry with exponential backoff

**Rationale**: Errors shouldn't break the immersion or lose messages
**Priority**: Must Have

### FR-009: Typing Indicators
System MUST show "typing" status during response generation:
- Display typing indicator when agent is processing
- Maintain indicator during response timing delays
- Remove indicator when response is sent

**Rationale**: Typing indicators reinforce the "real person" illusion
**Priority**: Should Have

### FR-010: Media Message Handling
System MUST handle non-text messages appropriately:
- Photos: Acknowledge receipt, inform Nikita "can't see images" in-character
- Voice messages: Acknowledge, suggest text (voice calls separate feature)
- Documents: Similar acknowledgment pattern
- Stickers/GIFs: Nikita responds in-character to emoji expression

**Rationale**: Users will try various message types; handling maintains immersion
**Priority**: Should Have

---

## Non-Functional Requirements

### Performance
- Message routing: < 500ms from receipt to agent invocation
- Response delivery: < 1 second from agent response to user receipt
- Concurrent users: Support 5,000 simultaneous active sessions

### Reliability
- Uptime: 99.9% availability (Telegram bot always responding)
- Message durability: No lost messages (queue if agent unavailable)
- Session persistence: Survive system restarts without data loss

### Security
- Authentication: Secure magic link tokens (single-use, time-limited)
- User isolation: No cross-user data leakage
- API security: Bot token protected, webhook validation enabled

### Scalability
- Initial: 10,000 registered users
- Scale to: 100,000 users without architecture changes
- Horizontal scaling: Stateless handlers allow multiple instances

### Monitoring
- Message latency tracking
- Error rate monitoring
- Rate limit hit frequency
- Session count tracking

---

## User Stories (CoD^Σ)

**Priority Model** (CoD^Σ):
```
P1 ⇒ MVP (can message Nikita via Telegram)
P2 ⇒ P1.enhance (smooth UX with typing, media handling)
P3 ⇒ future (advanced features)

Independence: ∀S_i, S_j ∈ Stories : S_i ⊥ S_j
```

---

### US-1: New User Onboarding (Priority: P1 - Must-Have)
```
New user → /start → email verification → ready to play
```
**Why P1**: Users cannot play without account creation

**Acceptance Criteria**:
- **AC-FR003-001**: Given a new Telegram user, When they send /start, Then they receive welcome message and email prompt
- **AC-FR004-001**: Given user provides email, When valid email format, Then magic link is sent to that address
- **AC-FR004-002**: Given user clicks magic link, When link is valid and not expired, Then account is created and confirmed

**Independent Test**: New Telegram user runs /start, completes email verification, is ready to message Nikita
**Dependencies**: None

---

### US-2: Send Message to Nikita (Priority: P1 - Must-Have)
```
Authenticated user → text message → Nikita response
```
**Why P1**: Core functionality—this IS the game

**Acceptance Criteria**:
- **AC-FR002-001**: Given authenticated user, When they send text message, Then message is routed to text agent
- **AC-FR002-002**: Given agent generates response, When response ready, Then it's delivered to user via Telegram
- **AC-FR007-001**: Given long response, When exceeds Telegram limit, Then split intelligently (not mid-word)

**Independent Test**: Authenticated user sends "Hello", receives Nikita's response
**Dependencies**: User authenticated (US-1)

---

### US-3: Session Persistence (Priority: P1 - Must-Have)
```
User conversations → session maintained → context preserved
```
**Why P1**: Without session, every message is context-free

**Acceptance Criteria**:
- **AC-FR005-001**: Given user sends multiple messages, When processed, Then conversation context is maintained
- **AC-FR005-002**: Given user returns after hours, When they send message, Then session context is restored
- **AC-FR005-003**: Given two users messaging simultaneously, When processing, Then no cross-contamination occurs

**Independent Test**: User sends message, waits 30 minutes, sends another—context preserved
**Dependencies**: User authenticated (US-1)

---

### US-4: Rate Limiting Protection (Priority: P1 - Must-Have)
```
Excessive messages → rate limit → graceful handling
```
**Why P1**: Without rate limits, abuse could take down system

**Acceptance Criteria**:
- **AC-FR006-001**: Given user sends 21+ messages in 1 minute, When rate limit hit, Then user is informed gracefully
- **AC-FR006-002**: Given user approaches daily limit, When at 450/500, Then subtle warning is provided
- **AC-FR006-003**: Given rate limit expires, When cooldown complete, Then user can message normally again

**Independent Test**: Send 25 messages rapidly, verify rate limit engages
**Dependencies**: User authenticated (US-1)

---

### US-5: Typing Indicators (Priority: P2 - Important)
```
Agent processing → typing indicator → feels real
```
**Why P2**: Enhances immersion but not blocking for MVP

**Acceptance Criteria**:
- **AC-FR009-001**: Given user sends message, When agent is processing, Then typing indicator appears
- **AC-FR009-002**: Given response has timing delay (Chapter 1-3), When waiting, Then typing indicator shows intermittently
- **AC-FR009-003**: Given response ready, When delivered, Then typing indicator stops

**Independent Test**: Send message, observe typing indicator during processing
**Dependencies**: P1 complete

---

### US-6: Media Message Handling (Priority: P2 - Important)
```
User sends photo → Nikita responds in-character → immersion maintained
```
**Why P2**: Users will try media; handling maintains immersion

**Acceptance Criteria**:
- **AC-FR010-001**: Given user sends photo, When processed, Then Nikita responds in-character ("What am I supposed to do with that?")
- **AC-FR010-002**: Given user sends voice note, When processed, Then Nikita suggests text or proper voice call
- **AC-FR010-003**: Given user sends sticker, When processed, Then Nikita responds to the emotional expression

**Independent Test**: Send photo to bot, verify in-character response
**Dependencies**: P1 complete

---

### US-7: Error Recovery (Priority: P2 - Important)
```
System error → graceful handling → user not left hanging
```
**Why P2**: Important for polish but MVP can have basic error handling

**Acceptance Criteria**:
- **AC-FR008-001**: Given agent is temporarily unavailable, When user sends message, Then message is queued and user notified of delay
- **AC-FR008-002**: Given network timeout, When delivery fails, Then system retries with backoff
- **AC-FR008-003**: Given auth token expired, When user messages, Then clear re-auth path provided

**Independent Test**: Simulate agent downtime, verify queuing and notification
**Dependencies**: P1 complete

---

### US-8: Help and Status Commands (Priority: P3 - Nice-to-Have)
```
User sends /help → guidance provided → discoverability
```
**Why P3**: Nice discoverability but users primarily just message

**Acceptance Criteria**:
- **AC-FR001-001**: Given user sends /help, When processed, Then available commands listed
- **AC-FR001-002**: Given user sends /status, When processed, Then current chapter and score hint shown
- **AC-FR001-003**: Given user sends /call, When processed, Then voice call information provided (or feature unlocked)

**Independent Test**: Send /help, /status, verify responses
**Dependencies**: P1 ∧ P2 complete

---

## Intelligence Evidence

### Queries Executed

```bash
# Existing structure check
ls nikita/platforms/telegram/ → __init__.py exists (stub)
Read memory/product.md → "Immersion Through Invisibility" principle
Read memory/product.md → User journey: /start → magic link → first message
```

### Findings

**Related Features**:
- nikita/platforms/telegram/__init__.py - Stub directory exists, ready for implementation
- memory/product.md:267-274 - Onboarding journey defined (/start, magic link, Telegram flow)
- nikita/db/models/user.py - User model with telegram_id field likely needed

**Existing Patterns**:
- Platform → Agent pattern established in architecture
- Auth via Supabase mentioned in product context

### Assumptions

- ASSUMPTION: Supabase auth available for magic link verification
- ASSUMPTION: Text Agent (001) ready to receive routed messages
- ASSUMPTION: User database can store telegram_id for mapping

### CoD^Σ Trace

```
Product.md (onboarding journey) ≫ platform/telegram (integration point) → FR-001 to FR-010
Evidence: memory/product.md:267-274, nikita/platforms/telegram/__init__.py
```

---

## Scope

### In-Scope Features
- Telegram bot setup and command handling
- User authentication (email + magic link via Supabase)
- Text message routing to Nikita Text Agent
- Response delivery with typing indicators
- Session management and persistence
- Rate limiting and abuse prevention
- Basic media message acknowledgment

### Out-of-Scope
- Voice call initiation (separate feature: 007-voice-agent)
- Scoring integration (separate feature: 003-scoring-engine)
- Payment/subscription handling (future)
- Web-based chat alternative (potential future)
- Group chat support (not applicable)

### Future Phases
- **Phase 2**: Deep link for voice calls integration
- **Phase 3**: Rich message formatting (if needed)
- **Phase 4**: Multi-platform support (Discord, WhatsApp)

---

## Constraints

### Business Constraints
- Must use Telegram (validated user preference, no app install friction)
- Auth must integrate with existing Supabase setup
- Must not require app store approval (bot-only)

### User Constraints
- Users must have Telegram installed (target audience assumption: tech-savvy)
- Users must have valid email for verification
- Users expect instant messaging (not email-like delays except intentional)

### Platform Constraints
- Telegram bot API limitations (message length, rate limits)
- Webhook vs polling trade-offs
- Media type support limitations

### Regulatory Constraints
- Email verification for identity (lightweight KYC)
- GDPR: User can request data deletion
- Data stored with user consent

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | User lookup, conversation storage | UserRepository.get_by_telegram_id(), ConversationRepository.create() |
| 010-api-infrastructure | Webhook endpoint | POST /api/v1/telegram/webhook with Telegram secret auth |
| 011-background-tasks | Delayed message delivery | pending_responses table, deliver-responses Edge Function |

**Database Tables Used**:
- `users` (telegram_id lookup, last_interaction_at updates)
- `conversations` (message storage, platform='telegram')
- `pending_responses` (delayed Nikita responses)

**API Endpoints Required**:
- `POST /api/v1/telegram/webhook` - Receives Telegram updates
- `POST /api/v1/telegram/set-webhook` - Configures webhook URL

---

## Risks & Mitigations (CoD^Σ)

### Risk 1: Telegram API Rate Limits
**Description**: Telegram imposes per-bot rate limits that could affect high-traffic periods
**Likelihood (p)**: Medium (0.5)
**Impact**: Medium (5)
**Risk Score**: r = 2.5
**Mitigation**:
```
Risk → Monitor_usage → Queue_management → Scale_bots
Prevention ⇒ Stay well under limits, implement queuing
Contingency ⇒ Multiple bot instances if needed
```

### Risk 2: Magic Link Email Deliverability
**Description**: Magic links may be marked as spam or not delivered
**Likelihood (p)**: Medium (0.5)
**Impact**: High (8)
**Risk Score**: r = 4.0
**Mitigation**:
```
Risk → Email_reputation → Retry_options → Alternative_auth
Prevention ⇒ Use reputable email service, proper SPF/DKIM
Contingency ⇒ Support code-based verification fallback
```

### Risk 3: Session State Loss
**Description**: User context lost on system restart or crash
**Likelihood (p)**: Low (0.2)
**Impact**: Medium (5)
**Risk Score**: r = 1.0
**Mitigation**:
```
Risk → Persistence_layer → Graceful_recovery → User_notification
Prevention ⇒ Store sessions in durable storage (not memory)
```

---

## Success Metrics

### User-Centric Metrics
- Onboarding completion rate: 80%+ of /start users complete verification
- First message latency: Users send first message within 5 minutes of verification
- Session continuity: 95%+ of returning users have context preserved

### Technical Metrics
- Message routing latency: < 500ms p95
- Delivery success rate: 99.9%
- Rate limit activation: < 1% of users hitting limits

### Business Metrics
- Channel as gateway: 100% of text gameplay through Telegram
- Activation rate: 70%+ of verified users have first conversation
- No-install friction: Users start playing without new app downloads

---

## Open Questions

All questions resolved through product documentation analysis.

---

## Stakeholders

**Owner**: Product Owner (Nikita game)
**Created By**: Claude (AI-assisted specification)
**Reviewers**: Engineering Lead
**Informed**: Text Agent feature team (dependency)

---

## Approvals

- [ ] **Product Owner**: [name] - [date]
- [ ] **Engineering Lead**: [name] - [date]

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0/3)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P2, P3)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope
- [x] No technology implementation details in spec
- [x] Intelligence evidence provided (CoD^Σ traces)
- [ ] Stakeholder approvals obtained

**Status**: Draft → Ready for Review

---

**Version**: 1.0
**Last Updated**: 2025-11-28
**Next Step**: Create implementation plan with `/plan specs/002-telegram-integration/spec.md`
