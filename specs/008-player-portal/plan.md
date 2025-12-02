# Implementation Plan: 008-Player-Portal

**Generated**: 2025-11-29
**Feature**: 008 - Player Portal (Web Dashboard)
**Input**: spec.md, Next.js + Supabase stack
**Priority**: P3 (Nice-to-Have)

---

## Overview

The Player Portal is a web dashboard providing visibility into relationship status, game progress, and history. It serves as the "behind the curtain" view while maintaining Telegram as the sole gameplay interface.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Player Portal                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Next.js Frontend                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │   │
│  │  │Dashboard │  │ History  │  │  Voice   │  │Settings │ │   │
│  │  │  View    │  │  Charts  │  │  Call    │  │  Page   │ │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │   │
│  │       │              │              │              │      │   │
│  │       └──────────────┼──────────────┼──────────────┘      │   │
│  │                      │              │                      │   │
│  │  ┌───────────────────┴──────────────┴────────────────┐   │   │
│  │  │              Supabase Client (Auth + DB)          │   │   │
│  │  └───────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                            │ API Calls                          │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Backend API (Cloud Run)                 │   │
│  │  GET /api/v1/portal/stats                               │   │
│  │  GET /api/v1/portal/conversations                       │   │
│  │  GET /api/v1/portal/score-history                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principle: View Only, No Gameplay

```
Portal CAN:
  ✓ View score, chapter, metrics
  ✓ View conversation history
  ✓ Initiate voice calls
  ✓ See decay warnings
  ✓ Manage settings

Portal CANNOT:
  ✗ Send messages to Nikita
  ✗ Reset decay timer
  ✗ Replace Telegram gameplay
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14+ (App Router) |
| UI Components | Shadcn/ui + Tailwind CSS |
| Charts | Recharts or Chart.js |
| Auth | Supabase Auth (magic link) |
| State | TanStack Query (React Query) |
| API Client | Supabase JS Client |
| Hosting | Vercel |

---

## Implementation Tasks

### Task 1: Create Portal Project Structure
**Directory**: `portal/` (separate Next.js app)

```
portal/
├── app/
│   ├── layout.tsx
│   ├── page.tsx (landing/login)
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── history/page.tsx
│   │   ├── call/page.tsx
│   │   └── settings/page.tsx
│   └── api/ (API routes if needed)
├── components/
│   ├── ui/ (shadcn components)
│   ├── dashboard/
│   ├── charts/
│   └── layout/
├── lib/
│   ├── supabase.ts
│   └── api.ts
└── hooks/
    └── use-player-data.ts
```

### Task 2: Implement Authentication
**File**: `portal/lib/supabase.ts`, `portal/app/login/page.tsx`

```typescript
// Supabase client with auth
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";

export const supabase = createClientComponentClient();

// Magic link login
async function loginWithMagicLink(email: string) {
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  return { error };
}
```

### Task 3: Implement Dashboard View
**File**: `portal/app/dashboard/page.tsx`

```typescript
export default function DashboardPage() {
  const { data: stats, isLoading } = usePlayerStats();

  if (isLoading) return <DashboardSkeleton />;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <ScoreCard score={stats.relationship_score} />
      <ChapterCard chapter={stats.chapter} name={stats.chapter_name} />
      <MetricsGrid metrics={stats.metrics} />
      <DecayWarning
        lastInteraction={stats.last_interaction_at}
        gracePeriod={stats.grace_period_hours}
      />
      <GameStatusBadge status={stats.game_status} />
    </div>
  );
}
```

### Task 4: Implement Score Chart
**File**: `portal/components/charts/score-chart.tsx`

```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface ScoreChartProps {
  data: ScoreHistoryEntry[];
  timeRange: "week" | "month" | "all";
}

export function ScoreChart({ data, timeRange }: ScoreChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <XAxis dataKey="date" />
        <YAxis domain={[0, 100]} />
        <Line
          type="monotone"
          dataKey="score"
          stroke="var(--primary)"
          strokeWidth={2}
        />
        <Tooltip content={<ScoreTooltip />} />
        {/* Mark significant events */}
        {data.filter(d => d.event).map(event => (
          <ReferenceDot
            key={event.id}
            x={event.date}
            y={event.score}
            r={6}
            fill="var(--accent)"
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Task 5: Implement Conversation History
**File**: `portal/app/dashboard/history/page.tsx`

```typescript
export default function HistoryPage() {
  const { data: conversations } = useConversationHistory();

  return (
    <div className="space-y-4">
      <ConversationFilters onFilter={handleFilter} />
      <ConversationList
        conversations={conversations}
        onSelect={handleSelect}
      />
      {selectedConversation && (
        <ConversationDetail
          conversation={selectedConversation}
          scoreImpact={selectedConversation.score_delta}
        />
      )}
    </div>
  );
}
```

### Task 6: Implement Voice Call Interface
**File**: `portal/app/dashboard/call/page.tsx`

```typescript
export default function VoiceCallPage() {
  const { data: availability } = useCallAvailability();
  const { initiateCall, isLoading } = useInitiateCall();

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      {availability.available ? (
        <>
          <CallButton
            onClick={initiateCall}
            isLoading={isLoading}
          />
          <p className="text-muted-foreground mt-4">
            Tap to call Nikita
          </p>
        </>
      ) : (
        <CallUnavailable reason={availability.reason} />
      )}
      <CallHistory calls={calls} />
    </div>
  );
}
```

### Task 7: Implement Decay Warning Component
**File**: `portal/components/dashboard/decay-warning.tsx`

```typescript
interface DecayWarningProps {
  lastInteraction: Date;
  gracePeriodHours: number;
  decayRate: number;
  currentScore: number;
}

export function DecayWarning({
  lastInteraction,
  gracePeriodHours,
  decayRate,
  currentScore,
}: DecayWarningProps) {
  const hoursRemaining = calculateHoursRemaining(lastInteraction, gracePeriodHours);
  const projectedScore = currentScore - (hoursRemaining < 0 ? decayRate : 0);

  return (
    <Card className={hoursRemaining < 6 ? "border-warning" : ""}>
      <CardHeader>
        <CardTitle>Decay Status</CardTitle>
      </CardHeader>
      <CardContent>
        {hoursRemaining > 0 ? (
          <div>
            <p>{hoursRemaining} hours until grace period expires</p>
            <p className="text-sm text-muted-foreground">
              Keep talking to Nikita to reset the timer
            </p>
          </div>
        ) : (
          <div className="text-warning">
            <p>⚠️ Decay active!</p>
            <p>Score: {currentScore}% → {projectedScore}%</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Task 8: Implement Settings Page
**File**: `portal/app/dashboard/settings/page.tsx`

```typescript
export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <NotificationSettings />
      <AccountSection>
        <DataExportButton />
        <DeleteAccountButton />
      </AccountSection>
      <LogoutButton />
    </div>
  );
}
```

### Task 9: Create Portal API Routes
**File**: `nikita/api/routes/portal.py`

```python
router = APIRouter(prefix="/portal", tags=["portal"])

@router.get("/stats/{user_id}")
async def get_player_stats(user_id: UUID, user: User = Depends(get_current_user)):
    """Get dashboard stats for player."""
    if user.id != user_id:
        raise HTTPException(403)

    stats = await portal_service.get_stats(user_id)
    return stats

@router.get("/score-history/{user_id}")
async def get_score_history(
    user_id: UUID,
    range: str = "week",
    user: User = Depends(get_current_user),
):
    """Get score history for charts."""
    history = await portal_service.get_score_history(user_id, range)
    return history

@router.get("/conversations/{user_id}")
async def get_conversations(
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
):
    """Get conversation history."""
    conversations = await portal_service.get_conversations(user_id, limit, offset)
    return conversations
```

---

## User Story Mapping

| User Story | Tasks | Components |
|------------|-------|------------|
| US-1: View Dashboard | T2, T3 | Auth, DashboardPage |
| US-2: Score History | T4 | ScoreChart |
| US-3: Voice Call | T6 | VoiceCallPage |
| US-4: Decay Status | T7 | DecayWarning |
| US-5: Conversation History | T5 | HistoryPage |
| US-6: Settings | T8 | SettingsPage |

---

## Implementation Order

```
Phase 1: Foundation
├── T1: Project structure
├── T2: Authentication
└── T9: Backend API routes

Phase 2: Dashboard (US-1)
├── T3: Dashboard view
└── T7: Decay warning

Phase 3: History (US-2, US-5)
├── T4: Score chart
└── T5: Conversation history

Phase 4: Voice & Settings (US-3, US-6)
├── T6: Voice call interface
└── T8: Settings page

Phase 5: Polish
├── Responsive design
├── Loading states
└── Error handling
```

---

## Constitution Alignment

**§I.1 Invisible Game Interface** (separation enforced):
- ✅ Portal is view-only, not gameplay
- ✅ Telegram remains sole interaction point
- ✅ Portal viewing does NOT reset decay

**§VI.2 UX Excellence**:
- ✅ Responsive design for all devices
- ✅ WCAG 2.1 AA accessibility
- ✅ Clear information hierarchy

**§VII.1 Test-Driven Development**:
- ✅ Tests before implementation
- ✅ Component tests with React Testing Library

---

## Dependencies

| Spec | Status | Blocking? |
|------|--------|-----------|
| 003-scoring-engine | ⏳ Audit PASS | Score display |
| 005-decay-system | ⏳ Audit PASS | Decay warnings |
| 007-voice-agent | ⏳ Audit PASS | Voice call button |
| 010-api-infrastructure | ✅ Audit PASS | API routes |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial plan from spec.md |
