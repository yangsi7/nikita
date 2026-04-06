# Portal Routes Reference — E2E Nikita v4

## Route Map (27 routes)

### Public Routes (no auth required)

| # | URL | Auth | Key Selectors | Common Failures |
|---|-----|------|----------------|-----------------|
| 1 | `/` | public | H1 "Dumped", `data-testid="chapter-dot"`, `data-testid="message-bubble"` | CSP blocks scripts, OG image missing |
| 2 | `/login` | public (redirects if authed) | Email input, submit button, Card component | Rate limit on OTP, redirect loop |
| 3 | `/auth/callback` | public | N/A (redirect handler) | Expired token, missing code param |
| 4 | `/auth/bridge` | public | N/A (redirect handler) | Invalid/expired bridge token |
| 5 | `/onboarding` | public | `data-testid="section-chapters"`, `data-testid="section-profile"`, `data-testid="onboarding-submit-btn"` | Scroll sections not triggering, API timeout |

### Player Routes (auth required — any authenticated user)

| # | URL | Auth | Key Selectors | Common Failures |
|---|-----|------|----------------|-----------------|
| 6 | `/dashboard` | player | `data-testid="card-score-ring"`, `data-testid="card-mood-orb"`, `data-testid="dashboard-empty-state"` | Blank page (Suspense), stale score cache |
| 7 | `/dashboard/engagement` | player | `data-testid="card-engagement-chart"` | Missing engagement_state row, chart render failure |
| 8 | `/dashboard/nikita` | player | `data-testid="card-mood-orb"`, nav cards | Empty life_events, loading stuck |
| 9 | `/dashboard/nikita/day` | player | Date nav buttons, events list | No life_events data, date parsing |
| 10 | `/dashboard/nikita/mind` | player | Thoughts list, "Load More" button | Empty thoughts, pagination offset error |
| 11 | `/dashboard/nikita/stories` | player | Arc cards, "Show resolved" toggle | No story arcs, toggle state not persisted |
| 12 | `/dashboard/nikita/circle` | player | Friend gallery, count badge | No friends data, empty gallery |
| 13 | `/dashboard/vices` | player | `data-testid="card-vice-{category}"` | No vices discovered, locked card render |
| 14 | `/dashboard/conversations` | player | Tabs (All/Text/Voice/Boss), conversation cards | Empty state, tab filter broken, pagination |
| 15 | `/dashboard/conversations/[id]` | player | Message bubbles (left/right aligned), score delta | Invalid ID 404, transcript empty |
| 16 | `/dashboard/insights` | player | `data-testid="chart-score-ring"` (reused), ThreadCards | Missing metrics, SVG render |
| 17 | `/dashboard/diary` | player | `data-testid="card-diary-{id}"` | No diary entries, emotional_tone null |
| 18 | `/dashboard/settings` | player | Timezone select, notification switch, delete button | API timeout on PUT, delete cascade failure |

### Admin Routes (auth required — admin role only)

| # | URL | Auth | Key Selectors | Common Failures |
|---|-----|------|----------------|-----------------|
| 19 | `/admin` | admin | 5 KPI cards (Total Users, Active, Boss, Game Over, Won) | Count query slow, NaN in cards |
| 20 | `/admin/users` | admin | `data-testid="table-users"`, search input, chapter filter, `data-testid="row-{id}"`, `data-testid="empty-users"` | Filter not clearing, sort broken |
| 21 | `/admin/users/[id]` | admin | GodModePanel (amber GlassCard, Shield icon), MutationDialogs | Mutation API 500, optimistic update stale |
| 22 | `/admin/pipeline` | admin | `data-testid="card-pipeline"` | No pipeline data, timing display NaN |
| 23 | `/admin/text` | admin | Conversation table, pagination | Empty state, wrong platform filter |
| 24 | `/admin/voice` | admin | Conversation table, duration column | No voice data, duration null |
| 25 | `/admin/conversations/[id]` | admin | SummaryCards, StageTimelineBar | Invalid ID, missing pipeline stages |
| 26 | `/admin/jobs` | admin | `data-testid="card-job-{name}"` (5 cards) | Job never ran, stale timestamps |
| 27 | `/admin/prompts` | admin | Prompts table, Sheet (side panel) | Sheet not opening, prompt content empty |

---

## Auth Routing Rules (from middleware.ts)

```
/ (landing)           → always public, never redirects
/login, /auth/*       → public; if authenticated → redirect to /dashboard (player) or /admin (admin)
/dashboard/*          → requires auth; no auth → redirect to /login
/admin/*              → requires auth + admin role; no auth → /login; no admin → /dashboard
/onboarding           → public (no middleware redirect; content gated by app logic)
```

### Admin Detection
```typescript
function isAdmin(u: User): boolean {
  return u.user_metadata?.role === "admin"
}
```

---

## Data-TestID Index

### Dashboard Components
| Selector | Component | Location |
|----------|-----------|----------|
| `card-score-ring` | RelationshipHero | `/dashboard` |
| `chart-score-ring` | ScoreRing SVG | `/dashboard`, `/insights` |
| `card-mood-orb` | MoodOrb | `/dashboard`, `/nikita` |
| `card-engagement-chart` | EngagementPulse | `/engagement` |
| `dashboard-empty-state` | DashboardEmptyState | `/dashboard` (no data) |
| `card-vice-{category}` | ViceCard | `/vices` |
| `card-diary-{id}` | DiaryEntry | `/diary` |

### Admin Components
| Selector | Component | Location |
|----------|-----------|----------|
| `table-users` | UserTable | `/admin/users` |
| `row-{id}` | UserTable row | `/admin/users` |
| `empty-users` | EmptyState | `/admin/users` (no match) |
| `card-pipeline` | PipelineBoard | `/admin/pipeline` |
| `card-job-{name}` | JobCard | `/admin/jobs` |

### Layout Components
| Selector | Component | Location |
|----------|-----------|----------|
| `nav-sidebar` | Sidebar | All authenticated pages |
| `nav-mobile` | MobileNav | All pages (375px viewport) |

### Landing / Onboarding
| Selector | Component | Location |
|----------|-----------|----------|
| `chapter-dot` | ChapterTimeline dots | `/` |
| `message-bubble` | TelegramMockup bubbles | `/` |
| `section-chapters` | ChapterSection | `/onboarding` |
| `section-score` | ScoreSection | `/onboarding` |
| `section-rules` | RulesSection | `/onboarding` |
| `section-profile` | ProfileSection | `/onboarding` |
| `section-mission` | MissionSection | `/onboarding` |
| `onboarding-submit-btn` | Submit button | `/onboarding` |
| `onboarding-mood-orb` | OnboardingMoodOrb | `/onboarding` |
| `onboarding-chapter-stepper` | ChapterStepper | `/onboarding` |

### Shared Components
| Selector | Component | Location |
|----------|-----------|----------|
| `empty-state` | EmptyState (default) | Various |
| `error-display` | ErrorDisplay | Any page on error |
| `skeleton-*` | LoadingSkeleton variants | Any loading state |
