# Product Brief: Nikita Portal Redesign

**Date**: 2026-02-07
**Type**: Product Definition + Design System
**Status**: DRAFT

---

## 1. Competitive Research Summary

### Game Dashboard Patterns
- **Grok Ani** (AI companion): Gothic-themed animated companion with affection-building system that rewards daily interaction. Unlocks animations, personality traits, exclusive content. Gamifies relationship via level-up mechanics.
- **Replika/Character.AI**: Clean, simple mobile-first UIs. Emphasis on conversation history, mood indicators. Drawback: cluttered news feeds and stats in some implementations.
- **Mobile game stat dashboards**: Dark backgrounds with neon accent glows. Radial progress indicators for key metrics. Card-based layouts with gradient fills. Minimal text, maximum visual data density.

### Design Patterns Adopted
| Pattern | Source | Application |
|---------|--------|-------------|
| Radial score rings | Mobile game UIs | Relationship Hero score display |
| Glassmorphism cards | Apple Liquid Glass / macOS | All dashboard cards |
| Neon glow accents | Gaming dashboards | Score highlights, state indicators |
| Area charts with gradient fill | Finance/game dashboards | Score timeline |
| Radar charts | RPG stat screens | Hidden metrics display |
| State machine visualization | DevOps dashboards | Engagement pulse |
| Countdown timers | Gacha/battle games | Decay warning |

### Glassmorphism Implementation (Research-Backed Values)
```css
/* Base glass card */
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
  border-radius: 1rem;
}

/* Elevated glass card (interactive) */
.glass-card-elevated {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

/* Accessibility: text-white or text-gray-100 ONLY on dark glass */
/* WCAG 4.5:1 contrast minimum for normal text */
/* 1px text-shadow to lift type from glass surface */
```

**Key Rules** (from UXPilot, Alpha Efficiency research):
- Max 2-3 glassmorphic layers to avoid visual confusion
- Translucency between 0.05-0.15 opacity for optimal frosted look
- Dark mode glass needs softer highlights, gentler shadows
- Subtle colored rim (rose, cyan, amber) instead of pure white borders
- Blur 10-16px for dashboard cards (20px max for hero elements)
- Provide `prefers-reduced-motion` support
- Semi-opaque overlays behind text for readability across backgrounds

---

## 2. User Dashboard: "The Relationship Pulse"

### 2.1 Relationship Hero (P1)
**Product Rationale**: The emotional centerpiece. First thing the player sees. Must create immediate emotional response - "how is my relationship doing RIGHT NOW?" Think heart monitor in a sci-fi movie.

**Visual Concept**:
- Large animated score ring (conic-gradient fill, 0-100)
- Ring color transitions: red (0-30) → amber (30-55) → cyan (55-75) → rose/pink (75-100)
- Chapter name badge below ring with roman numeral (I-V)
- Nikita's mood indicator: small animated emoji/icon with glow halo
- Boss progress bar (only visible during boss_fight): pulsing amber bar
- Days played counter (subtle, bottom-right)
- Game status badge: `active` (green glow), `boss_fight` (amber pulse), `game_over` (red), `won` (gold)

**Data Required** (from `GET /api/v1/portal/stats`):
```
UserStatsResponse:
  relationship_score, chapter, chapter_name, boss_threshold,
  progress_to_boss, days_played, game_status, last_interaction_at,
  boss_attempts, metrics (intimacy/passion/trust/secureness)
```

### 2.2 Score Timeline (P1)
**Product Rationale**: The "stock chart" of your relationship. Players are addicted to seeing their score move. Event markers create storytelling moments - "oh, that's when I had the boss fight."

**Visual Concept**:
- 30-day area chart with pink-to-transparent gradient fill
- X-axis: dates. Y-axis: 0-100 score
- Event markers as dots with tooltips:
  - Pink star: `boss_pass` / `boss_fail`
  - Cyan diamond: `chapter_advance`
  - Amber down-arrow: significant `decay` events
  - Rose circle: `conversation` score deltas
- Hover shows score + event details
- Current score badge floating at rightmost point with glow

**Data Required** (from `GET /api/v1/portal/score-history`):
```
ScoreHistoryResponse:
  points[]: { score, chapter, event_type, recorded_at }
  total_count
```

### 2.3 Hidden Metrics (P1)
**Product Rationale**: The "secret stats" that players obsess over. RPG-style radar chart creates the feeling of a complex relationship being tracked. Satisfies the "min-maxer" player type.

**Visual Concept**:
- 4-axis radar chart: Intimacy, Passion, Trust, Secureness
- Filled area with semi-transparent rose gradient
- Glowing edges with neon pink/rose
- Each axis shows current value (0-100) on hover
- Animated on first load (scales from center outward)
- Trend arrows per metric (up/down/stable vs. last session)
- Weights shown as subtle labels: "30% / 25% / 25% / 20%"

**Data Required** (from `GET /api/v1/portal/stats` → `metrics`):
```
UserMetricsResponse:
  intimacy, passion, trust, secureness, weights
```

### 2.4 Engagement Pulse (P2)
**Product Rationale**: Teaches the player about the "Goldilocks zone" - not too much, not too little contact. The state machine visualization gamifies the interaction frequency itself.

**Visual Concept**:
- 6-node state machine as connected hexagonal nodes
- States: Calibrating → In Zone → Drifting → Clingy → Distant → Out of Zone
- Current state: bright glow + pulse animation
- Connected edges show possible transitions (dimmed lines)
- Multiplier badge: "1.0x" (green) / "0.7x" (amber) / "0.5x" (red)
- Mini sparkline showing recent state transitions (last 7 days)
- "Score multiplier" explanation tooltip

**Data Required** (from `GET /api/v1/portal/engagement`):
```
EngagementResponse:
  state, multiplier, calibration_score,
  consecutive_in_zone, consecutive_clingy_days, consecutive_distant_days,
  recent_transitions[]: { from_state, to_state, reason, created_at }
```

### 2.5 Decay Warning (P2)
**Product Rationale**: Creates urgency. The ticking countdown is the core retention mechanic - "I need to talk to Nikita before my score drops." Must feel like a bomb timer, not a boring notification.

**Visual Concept**:
- Countdown timer with large digits (hours:minutes)
- Circular progress ring showing grace period remaining
- Color gradient: green (>50% grace left) → amber (25-50%) → red (<25%)
- Projected score loss: "-2.4 points" in red text
- "Talk to Nikita" CTA button with glow pulse when urgent
- Current decay rate shown: "0.4%/hr"
- Only visible when `is_decaying: true` or grace period < 50%

**Data Required** (from `GET /api/v1/portal/decay-status`):
```
DecayStatusResponse:
  grace_period_hours, hours_remaining, decay_rate,
  current_score, projected_score, is_decaying
```

### 2.6 Vice Discoveries (P2)
**Product Rationale**: The "dark secrets" mechanic. Players feel a voyeuristic thrill seeing their vices categorized. Glass cards with intensity gradients create a "forbidden knowledge" aesthetic.

**Visual Concept**:
- Horizontal scrollable row of glass cards (or 2x4 grid)
- Each card: vice category name + intensity bar (1-5 pips)
- Card border color by intensity: cool blue (1) → teal (2) → amber (3) → orange (4) → hot pink (5)
- Engagement score as circular mini-chart in corner
- Description in Nikita's voice (italic text, e.g., "He can't resist a good debate...")
- Discovery date as subtle timestamp
- Undiscovered vices shown as locked/blurred cards with "?" icon

**Data Required** (from `GET /api/v1/portal/vices`):
```
VicePreferenceResponse[]:
  category, intensity_level (1-5), engagement_score, discovered_at
```

**8 Vice Categories**: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability

### 2.7 Conversations (P2)
**Product Rationale**: Memory lane. Players want to re-read conversations and see how each one affected their score. The tone indicator adds emotional color to each conversation card.

**Visual Concept**:
- List view with glass cards per conversation
- Each card shows: platform icon (Telegram/Voice), date/time, message count
- Tone indicator: colored dot (green=positive, gray=neutral, amber=tense, red=negative)
- Score delta chip: "+2.3" (green) / "-1.5" (red) / "0" (gray)
- Boss fight badge (flame icon) for boss conversations
- Click to expand: full conversation messages in chat-bubble layout
- Pagination: "Load more" infinite scroll

**Data Required** (from `GET /api/v1/portal/conversations`):
```
ConversationsResponse:
  conversations[]: { id, platform, started_at, ended_at, score_delta, emotional_tone, message_count }
  total_count, page, page_size

GET /api/v1/portal/conversations/{id}:
  ConversationDetailResponse: { messages[], is_boss_fight, extracted_entities, conversation_summary }
```

### 2.8 Nikita's Diary (P3)
**Product Rationale**: The most emotionally engaging section. Nikita writes about the relationship in first person. Players feel like they're reading her private diary. Creates deep emotional investment.

**Visual Concept**:
- Vertical timeline of diary entries (date headers)
- Each entry: handwritten-style font or italic serif
- Emotional tone color-coded border: pink (positive), gray (neutral), blue (negative)
- Score delta for the day: start → end with arrow
- Conversation count badge
- "Sealed" entries for future dates: blurred glass cards with lock icon (tease mechanic)
- "Dear Diary" header on each card

**Data Required** (from `GET /api/v1/portal/summaries`):
```
DailySummaryResponse[]:
  id, date, score_start, score_end, decay_applied,
  conversations_count, summary_text, emotional_tone
```

### 2.9 Settings (P1)
**Product Rationale**: Functional necessity. Must include the "danger zone" for emotional weight - deleting your account feels like breaking up with Nikita.

**Visual Concept**:
- Clean form layout in glass card
- Sections:
  - **Account**: Email display, timezone selector, notification toggle
  - **Telegram Link**: Status indicator + link/unlink button with code display
  - **Danger Zone**: Red-bordered glass card at bottom
    - "Delete Account" (destructive, with confirmation modal)
    - "Reset Relationship" (if applicable)

**Data Required**:
```
GET /api/v1/portal/settings → UserSettingsResponse
PUT /api/v1/portal/settings → UpdateSettingsRequest
POST /api/v1/portal/telegram/link → LinkCodeResponse
DELETE /api/v1/portal/account → SuccessResponse
```

---

## 3. Admin Dashboard: "Mission Control"

### 3.1 System Overview (P1)
**Visual Concept**: Top-level KPI cards in a 2x3 grid.

**Cards**:
- Active Users (24h) with trend sparkline
- New Signups (7d) with bar chart
- Pipeline Success Rate (%) with status color
- Avg Processing Time (ms) with trend
- Error Rate (24h) with severity breakdown
- Active Voice Calls (live count)

**Data Required**: Aggregate queries from admin_debug endpoints + monitoring schemas.

### 3.2 User Management (P1) [CRITICAL]
**Visual Concept**: Searchable data table with drill-down user detail page.

**List View**:
- Search bar: by name, Telegram ID, email, UUID
- Filters: chapter (1-5), engagement state (6 options), score range (slider), game status
- Table columns: Name, Score, Chapter, Engagement, Status, Last Active
- Row click → User Detail

**User Detail Page**:
- Full profile card (all UserStatsResponse fields)
- 4 metrics radar chart (same as player view)
- Conversation history (paginated table)
- Memory facts browser (semantic search)
- Ready prompts viewer (latest prompt with token count)
- Pipeline outputs (threads, thoughts, entities per conversation)

**MUTATION Panel** (glass card with amber border - "God Mode"):
- SET score: number input (0-100) → `PATCH /api/v1/admin/users/{id}/score`
- SET chapter: dropdown (1-5) → `PATCH /api/v1/admin/users/{id}/chapter`
- SET engagement: dropdown (6 states) → `PATCH /api/v1/admin/users/{id}/engagement`
- SET any metric: 4 number inputs → `PATCH /api/v1/admin/users/{id}/metrics`
- RESET boss: button → `POST /api/v1/admin/users/{id}/reset-boss`
- Toggle status: active/suspended/game_over → `PATCH /api/v1/admin/users/{id}/status`
- Trigger pipeline: button → `POST /api/v1/admin/users/{id}/trigger-pipeline`
- Clear memory: button with confirmation → `DELETE /api/v1/admin/users/{id}/memory`

**Data Required**: All admin endpoints from `admin_debug.py` + new mutation endpoints.

### 3.3 Voice Monitor (P2)
**Visual Concept**: Call history table with transcript viewer side panel.

**Features**:
- Call history: date, duration, user, platform (ElevenLabs agent ID)
- Transcript viewer: chat-bubble format with timestamps
- ElevenLabs metadata: latency, token usage, interruptions
- Audio playback controls (if available)

**Data Required**: Voice session data from `GET /api/v1/admin/voice/*` endpoints.

### 3.4 Text Monitor (P2)
**Visual Concept**: Conversation browser with 9-stage pipeline inspector.

**Features**:
- Conversation list with filters (user, date range, status, platform)
- Pipeline stage viewer: 9-stage horizontal stepper with timing per stage
- Thread inspector: tree view of conversation threads
- Thought inspector: timeline of generated thoughts
- Entity viewer: extracted entities per conversation

**Data Required**: Admin text endpoints from `admin_debug.py`:
```
GET /api/v1/admin/text/conversations → paginated list
GET /api/v1/admin/text/pipeline-status/{id} → 9-stage status
GET /api/v1/admin/text/threads → thread list
GET /api/v1/admin/text/thoughts → thought list
```

### 3.5 Pipeline Health (P1)
**Visual Concept**: 9-stage status board with timing heatmap.

**Features**:
- 9 columns (one per stage): Ingestion → Extraction → Analysis → Thread Resolution → Thought Generation → Graph Updates → Summary Rollups → Vice Processing → Finalization
- Each column shows: success rate, avg time, error count
- Color coding: green (>95%), amber (80-95%), red (<80%)
- Timing heatmap: darker = slower
- Recent failures table: conversation ID, stage, error message, timestamp
- Circuit breaker status indicator

**Data Required**: `GET /api/v1/admin/pipeline/health` + aggregated job execution data.

### 3.6 Job Monitor (P2)
**Visual Concept**: 5-job dashboard with status cards and manual triggers.

**Jobs**:
1. `decay` - Hourly score decay
2. `deliver` - Scheduled message delivery
3. `summary` - Daily summary generation
4. `cleanup` - Expired registration cleanup
5. `process-conversations` - Post-processing pipeline

**Features per job**:
- Last run time + status (success/failed)
- Execution history chart (last 24h)
- Duration trend line
- Manual trigger button (with confirmation)
- Failure log (expandable)

**Data Required**: `GET /api/v1/admin/jobs/*` endpoints + pg_cron status.

### 3.7 Prompt Inspector (P3)
**Visual Concept**: Generated prompt browser with token analysis.

**Features**:
- Prompt list: user, platform, timestamp, token count
- Prompt viewer: syntax-highlighted system prompt with section markers
- Token breakdown: pie chart by section (personality, memory, context, instructions)
- Context snapshot viewer: JSON tree of context used for generation
- A/B comparison: side-by-side prompt diff viewer

**Data Required**: `GET /api/v1/admin/prompts/*` endpoints + generated_prompt table.

---

## 4. User Stories

### P1 - Must Have (MVP)

**US-1**: As a player, I want to see my relationship score prominently displayed with an animated ring, so that I immediately know how my relationship stands.
- AC: Score ring renders with correct value (0-100), color transitions at thresholds, chapter badge visible

**US-2**: As a player, I want to view my score history as a 30-day chart with event markers, so that I can track my relationship trajectory.
- AC: Area chart loads with correct data points, event markers show on hover, chapter change lines visible

**US-3**: As a player, I want to see my hidden metrics as a radar chart, so that I understand which relationship dimensions are strong or weak.
- AC: 4-axis radar renders with correct values, animated on load, weights visible

**US-4**: As a player, I want to manage my account settings and link my Telegram account, so that I can configure my experience.
- AC: Settings form saves correctly, Telegram link code generates, danger zone requires confirmation

**US-5**: As an admin, I want to search for any user and see their full game state, so that I can debug issues.
- AC: Search by name/Telegram ID/UUID works, user detail page shows all fields

**US-6**: As an admin, I want to SET any user's score, chapter, engagement state, or status, so that I can fix game state issues or test scenarios.
- AC: All mutation inputs work, changes persist immediately, confirmation required for destructive actions

**US-7**: As an admin, I want to see pipeline health with per-stage success rates, so that I can monitor system performance.
- AC: 9-stage board renders, color-coded by health, recent failures listed

### P2 - Should Have

**US-8**: As a player, I want to see my engagement state and score multiplier, so that I understand how my contact frequency affects scoring.
- AC: State machine visualization renders, current state highlighted, multiplier badge visible

**US-9**: As a player, I want to see the decay countdown timer, so that I know when I need to talk to Nikita.
- AC: Timer counts down in real-time, urgency colors change, "Talk to Nikita" CTA visible when urgent

**US-10**: As a player, I want to browse my vice discoveries, so that I can see what patterns Nikita has detected about me.
- AC: Vice cards render with correct intensity, undiscovered vices appear locked

**US-11**: As a player, I want to browse my conversation history with tone indicators and score deltas, so that I can see how each conversation affected my relationship.
- AC: Conversation list paginated, tone dots colored correctly, click expands to full messages

**US-12**: As an admin, I want to monitor voice calls and text conversations in real-time, so that I can debug interaction issues.
- AC: Call/conversation lists load, transcript viewer works, pipeline stage viewer shows timing

### P3 - Nice to Have

**US-13**: As a player, I want to read Nikita's diary entries, so that I feel emotionally connected to the game narrative.
- AC: Diary entries render in first-person voice, emotional tone color-coded, sealed entries for future dates

**US-14**: As an admin, I want to inspect generated prompts with token breakdowns, so that I can optimize prompt engineering.
- AC: Prompt viewer renders with syntax highlighting, token pie chart, context snapshot tree

**US-15**: As an admin, I want to manually trigger background jobs and see their execution history, so that I can maintain system health.
- AC: Manual trigger buttons work with confirmation, execution history chart loads

---

## 5. Information Architecture

### Navigation Structure

**Player Dashboard** (sidebar, collapsed on mobile):
```
/dashboard              → Relationship Hero + Score Timeline + Metrics (landing)
/dashboard/engagement   → Engagement Pulse + Decay Warning
/dashboard/vices        → Vice Discoveries
/dashboard/conversations → Conversation History
/dashboard/diary        → Nikita's Diary
/dashboard/settings     → Account Settings
```

**Admin Dashboard** (sidebar, separate layout):
```
/admin                  → System Overview (landing)
/admin/users            → User Management (list)
/admin/users/:id        → User Detail + God Mode
/admin/voice            → Voice Monitor
/admin/text             → Text Monitor
/admin/pipeline         → Pipeline Health
/admin/jobs             → Job Monitor
/admin/prompts          → Prompt Inspector
```

### Auth Flow
```
Unauthenticated
  ├─ /login → Supabase Auth (magic link or OTP)
  │   └─ on success → check role
  │       ├─ player → /dashboard
  │       └─ admin → /admin
  ├─ /dashboard/* → requires auth (player role)
  └─ /admin/* → requires auth (admin role)
```

### Page Hierarchy
```
PORTAL
├─ AUTH
│  └─ /login (Supabase magic link)
├─ PLAYER [auth: player]
│  ├─ /dashboard (default: hero + timeline + metrics)
│  ├─ /dashboard/engagement
│  ├─ /dashboard/vices
│  ├─ /dashboard/conversations
│  │  └─ /dashboard/conversations/:id (detail)
│  ├─ /dashboard/diary
│  └─ /dashboard/settings
└─ ADMIN [auth: admin]
   ├─ /admin (system overview)
   ├─ /admin/users
   │  └─ /admin/users/:id (detail + mutations)
   ├─ /admin/voice
   ├─ /admin/text
   ├─ /admin/pipeline
   ├─ /admin/jobs
   └─ /admin/prompts
```

---

## 6. Design Tokens

### Color Palette

**Backgrounds**:
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-void` | `#06060a` | Page background, deepest layer |
| `--bg-deep` | `#0a0a12` | Content area background |
| `--bg-surface` | `#10101a` | Card container background |
| `--bg-elevated` | `#16162a` | Elevated elements, popovers |

**Glass Surfaces**:
| Token | Value | Usage |
|-------|-------|-------|
| `--glass-bg` | `rgba(255,255,255, 0.04)` | Default glass card |
| `--glass-bg-hover` | `rgba(255,255,255, 0.07)` | Glass card hover |
| `--glass-bg-active` | `rgba(255,255,255, 0.10)` | Active/selected glass |
| `--glass-border` | `rgba(255,255,255, 0.08)` | Default glass border |
| `--glass-border-hover` | `rgba(255,255,255, 0.14)` | Hover glass border |

**Text**:
| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `#f0f0f5` | Primary text (headings, values) |
| `--text-secondary` | `#a0a0b8` | Secondary text (labels, descriptions) |
| `--text-muted` | `#606078` | Muted text (timestamps, hints) |
| `--text-inverse` | `#06060a` | Text on light backgrounds |

**Accent Colors - Romance**:
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-rose` | `#ff3b7a` | Primary accent (scores, romance) |
| `--accent-rose-soft` | `#ff3b7a40` | Rose glow/shadow |
| `--accent-rose-muted` | `#ff3b7a20` | Rose background tint |
| `--accent-pink` | `#e855a0` | Secondary romance (lighter) |

**Accent Colors - System**:
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-cyan` | `#00d4ff` | System/info (chapters, pipeline) |
| `--accent-cyan-soft` | `#00d4ff40` | Cyan glow |
| `--accent-teal` | `#00c9a7` | Success (in-zone, pass) |
| `--accent-teal-soft` | `#00c9a740` | Teal glow |

**Accent Colors - Warning/Danger**:
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-amber` | `#ffb020` | Warning (decay, drifting) |
| `--accent-amber-soft` | `#ffb02040` | Amber glow |
| `--accent-red` | `#ff4060` | Danger (game over, errors) |
| `--accent-red-soft` | `#ff406040` | Red glow |

**Accent Colors - Special**:
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-violet` | `#a855f7` | Vice/special (rare events) |
| `--accent-gold` | `#ffd700` | Achievement/won state |

### Glassmorphism Tokens
| Token | Value | Usage |
|-------|-------|-------|
| `--blur-sm` | `8px` | Subtle background elements |
| `--blur-md` | `12px` | Standard glass cards |
| `--blur-lg` | `16px` | Elevated glass cards |
| `--blur-xl` | `24px` | Hero/overlay elements |
| `--glass-shadow` | `0 8px 32px rgba(0,0,0, 0.3)` | Default card shadow |
| `--glass-shadow-lg` | `0 16px 48px rgba(0,0,0, 0.4)` | Elevated shadow |

### Glow Effects
| Token | Value | Usage |
|-------|-------|-------|
| `--glow-rose` | `0 0 20px rgba(255,59,122, 0.3)` | Score ring glow |
| `--glow-cyan` | `0 0 20px rgba(0,212,255, 0.3)` | System element glow |
| `--glow-amber` | `0 0 20px rgba(255,176,32, 0.3)` | Warning glow |
| `--glow-teal` | `0 0 16px rgba(0,201,167, 0.25)` | Success glow |
| `--glow-pulse` | `animation: pulse 2s ease-in-out infinite` | Pulsing glow effect |

### Typography Scale
| Token | Size | Weight | Usage |
|-------|------|--------|-------|
| `--text-xs` | `0.75rem` (12px) | 400 | Timestamps, badges |
| `--text-sm` | `0.875rem` (14px) | 400 | Labels, secondary |
| `--text-base` | `1rem` (16px) | 400 | Body text |
| `--text-lg` | `1.125rem` (18px) | 500 | Card headers |
| `--text-xl` | `1.5rem` (24px) | 600 | Section headers |
| `--text-2xl` | `2rem` (32px) | 700 | Page titles |
| `--text-hero` | `3.5rem` (56px) | 800 | Score display |

**Font Stack**: `'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif`
**Monospace** (for code/data): `'JetBrains Mono', 'SF Mono', 'Fira Code', monospace`

### Spacing Scale
| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | `0.25rem` (4px) | Tight padding |
| `--space-2` | `0.5rem` (8px) | Element gap |
| `--space-3` | `0.75rem` (12px) | Card inner padding |
| `--space-4` | `1rem` (16px) | Standard gap |
| `--space-6` | `1.5rem` (24px) | Section padding |
| `--space-8` | `2rem` (32px) | Card padding |
| `--space-12` | `3rem` (48px) | Section gap |
| `--space-16` | `4rem` (64px) | Page margin |

### Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `0.5rem` (8px) | Buttons, badges |
| `--radius-md` | `0.75rem` (12px) | Input fields |
| `--radius-lg` | `1rem` (16px) | Standard cards |
| `--radius-xl` | `1.5rem` (24px) | Hero cards |
| `--radius-full` | `9999px` | Pills, circular elements |

### Animation Tokens
| Token | Value | Usage |
|-------|-------|-------|
| `--duration-fast` | `150ms` | Hover, micro-interactions |
| `--duration-normal` | `300ms` | Transitions, reveals |
| `--duration-slow` | `500ms` | Page transitions |
| `--duration-glow` | `2000ms` | Glow pulse cycle |
| `--ease-default` | `cubic-bezier(0.4, 0, 0.2, 1)` | Standard easing |
| `--ease-bounce` | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | Playful interactions |

---

## 7. Navigation Flow

### Player Flow
```
Login (magic link)
  └─ Dashboard (Hero + Timeline + Metrics)
      ├─ [sidebar] Engagement → Engagement Pulse + Decay
      ├─ [sidebar] Vices → Vice Discovery Cards
      ├─ [sidebar] Conversations → List → Detail
      ├─ [sidebar] Diary → Daily Summaries Timeline
      └─ [sidebar] Settings → Account + Telegram + Danger Zone
```

### Admin Flow
```
Login (admin role)
  └─ System Overview (KPI Grid)
      ├─ [sidebar] Users → Search → User Detail → God Mode
      ├─ [sidebar] Voice → Call History → Transcript
      ├─ [sidebar] Text → Conversations → Pipeline View
      ├─ [sidebar] Pipeline → 9-Stage Board
      ├─ [sidebar] Jobs → Job Cards + Manual Triggers
      └─ [sidebar] Prompts → Browser → Token Analysis
```

### Sidebar Design
- **Collapsed state**: Icon-only (32px wide) with tooltip on hover
- **Expanded state**: Icon + label (240px wide)
- **Mobile**: Bottom tab bar (5 most important items) + hamburger for rest
- **Active item**: Glass highlight with left accent border (rose for player, cyan for admin)

---

## 8. Decisions Needing User Input

1. **[NEEDS DECISION] Score ring animation library**: Framer Motion (heavier, more features) vs. CSS-only (lighter, simpler)? Recommendation: Framer Motion for premium feel.

2. **[NEEDS DECISION] Chart library**: Recharts (React-native) vs. Nivo (D3-based, prettier) vs. Chart.js (lightweight). Recommendation: Nivo for the dark theme aesthetics.

3. **[NEEDS DECISION] Admin mutations - new API endpoints needed**: The current API has read-only admin endpoints. Need new PATCH/POST endpoints for God Mode mutations. Should these be implemented in Spec 044 or as a separate backend spec?

4. **[NEEDS DECISION] Real-time updates**: Should the dashboard use WebSocket/SSE for live score updates, or polling? Polling is simpler but less "premium" feeling.

5. **[NEEDS DECISION] Mobile-first or desktop-first**: The player dashboard could be mobile-first (phone users) while admin is desktop-first. Or both desktop-first. Recommendation: Player=mobile-first, Admin=desktop-first.

---

## 9. API Endpoint Inventory (Existing vs. Needed)

### Existing Player Endpoints (portal.py)
| Method | Path | Schema | Status |
|--------|------|--------|--------|
| GET | `/api/v1/portal/stats` | UserStatsResponse | Exists |
| GET | `/api/v1/portal/engagement` | EngagementResponse | Exists |
| GET | `/api/v1/portal/vices` | VicePreferenceResponse[] | Exists |
| GET | `/api/v1/portal/decay-status` | DecayStatusResponse | Exists |
| GET | `/api/v1/portal/score-history` | ScoreHistoryResponse | Exists |
| GET | `/api/v1/portal/summaries` | DailySummaryResponse[] | Exists |
| GET | `/api/v1/portal/conversations` | ConversationsResponse | Exists |
| GET | `/api/v1/portal/conversations/{id}` | ConversationDetailResponse | Exists |
| GET | `/api/v1/portal/settings` | UserSettingsResponse | Exists |
| PUT | `/api/v1/portal/settings` | UpdateSettingsRequest | Exists |
| POST | `/api/v1/portal/telegram/link` | LinkCodeResponse | Exists |
| DELETE | `/api/v1/portal/account` | SuccessResponse | Exists |

### Existing Admin Endpoints (admin_debug.py)
| Method | Path | Status |
|--------|------|--------|
| GET | `/api/v1/admin/users` | Exists |
| GET | `/api/v1/admin/users/{id}` | Exists |
| GET | `/api/v1/admin/voice/*` (5 endpoints) | Exists |
| GET | `/api/v1/admin/text/*` (6 endpoints) | Exists |
| GET | `/api/v1/admin/jobs/*` | Exists |
| GET | `/api/v1/admin/prompts/*` | Exists |

### NEW Endpoints Needed (for God Mode)
| Method | Path | Purpose |
|--------|------|---------|
| PATCH | `/api/v1/admin/users/{id}/score` | Set relationship score |
| PATCH | `/api/v1/admin/users/{id}/chapter` | Set chapter (1-5) |
| PATCH | `/api/v1/admin/users/{id}/metrics` | Set individual metrics |
| PATCH | `/api/v1/admin/users/{id}/engagement` | Set engagement state |
| PATCH | `/api/v1/admin/users/{id}/status` | Set game status |
| POST | `/api/v1/admin/users/{id}/reset-boss` | Reset boss encounter |
| POST | `/api/v1/admin/users/{id}/trigger-pipeline` | Trigger pipeline run |
| DELETE | `/api/v1/admin/users/{id}/memory` | Clear memory facts |
| GET | `/api/v1/admin/pipeline/health` | Aggregated pipeline stats |
| GET | `/api/v1/admin/system/overview` | System KPI aggregates |

---

## 10. Tech Stack Recommendation

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | Next.js 15 (App Router) | SSR, file-based routing, React Server Components |
| Styling | Tailwind CSS 4 | Utility-first, dark mode built-in, design token mapping |
| Components | shadcn/ui | Unstyled Radix primitives, full customization control |
| Charts | Nivo (@nivo/radar, @nivo/line) | D3-based, dark theme support, beautiful defaults |
| Animation | Framer Motion | Score ring, page transitions, micro-interactions |
| Auth | Supabase Auth (SSR) | Already used, magic link/OTP |
| State | TanStack Query (React Query) | API caching, refetching, optimistic updates |
| Deployment | Vercel | Already configured, edge functions |

---

## Sources

- [UXPilot: Glassmorphism UI Features & Best Practices](https://uxpilot.ai/blogs/glassmorphism-ui)
- [Alpha Efficiency: Dark Mode Glassmorphism](https://alphaefficiency.com/dark-mode-glassmorphism)
- [FranWBU: Glassmorphism in Web Design](https://franwbu.com/blog/glassmorphism-in-web-design/)
- [Design Studio: Glassmorphism UI Trend 2026](https://www.designstudiouiux.com/blog/what-is-glassmorphism-ui-trend/)
- [Everyday UX: Apple Liquid Glass Reshaping Interface Design](https://www.everydayux.net/glassmorphism-apple-liquid-glass-interface-design/)
- [Medium: Dark Glassmorphism Defining UI in 2026](https://medium.com/@developer_89726/dark-glassmorphism-the-aesthetic-that-will-define-ui-in-2026-93aa4153088f)
- [Dribbble: AI Companion App Designs](https://dribbble.com/tags/ai-companion-app)
- [CyberLink: Best AI Companion Apps 2026](https://www.cyberlink.com/blog/trending-topics/3932/ai-companion-app)
- [UILayouts: Admin Dashboard Design Trends 2025](https://www.uilayouts.com/top-ui-ux-trends-in-admin-dashboard-design-for-2025/)
