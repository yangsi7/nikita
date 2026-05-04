# portal/src/app/dashboard/nikita/ — Nikita's World (Player View)

## Purpose

Player-facing window into Nikita's inner life: emotional state, life events (Spec 110 life-sim), thoughts (psyche agent output), social circle (NPCs from `life_simulation`), and day-by-day activity. Not the chat interface — this is the AMBIENT layer that makes Nikita feel alive between text/voice exchanges.

## Key Files

- `page.tsx` + `page-client.tsx` — hub view (`NikitaHubPage`):
  - `useEmotionalState()` (`@/hooks/use-emotional-state`) — current mood + conflict state.
  - `useLifeEvents()` — recent life-sim events (Spec 110 `pipeline_events` + life-sim outputs).
  - `useThoughts()` — psyche agent output stream.
  - `<MoodOrb />`, `<ConflictBanner />`, `<LifeEventTimeline />`, `<ThoughtFeed />` composite components.
- `mind/page.tsx` + `page-client.tsx` — detailed psyche / thought log (full `nikita_thoughts` table view).
- `circle/page.tsx` + `page-client.tsx` — Nikita's social circle (NPCs from `life_simulation/entity_manager.py`).
- `day/page.tsx` + `page-client.tsx` — day-by-day activity timeline (life events grouped by day).
- `stories/page.tsx` + `page-client.tsx` — narrative arcs (Spec 110 narrative manager).

All sub-pages mark `"use client"`; data via React Query hooks against the FastAPI backend.

## Callers

- Player nav from `portal/src/app/dashboard/page.tsx` (main dashboard) — Nikita's World card or tab.
- Deep links from push notifications (e.g., "Nikita had a tough day — see what happened" → `/dashboard/nikita/day`).
- Marketing surfaces eventually (gated demo).

## Gotchas

- **Read-only surface**: this dashboard MUST NOT mutate. All actions (send message, etc.) go through Telegram/voice/admin paths, never from `/dashboard/nikita/*`.
- **Hook ordering**: `useEmotionalState` is the gating query (`moodLoading` controls the skeleton). `useLifeEvents` and `useThoughts` are lazy and don't block first paint. If you reorder, verify the loading skeleton still triggers on first paint.
- **`emotional_state.conflict_state`** drives `<ConflictBanner />` (`page-client.tsx:40-`). Values per `nikita/db/models/user.py` (or wherever `ConflictType` enum lives) — confirm before adding new banner variants. The "none" string check at `:40` is brittle; consider exposing a typed enum import.
- **Life-sim emptiness**: cold users (first-day, no scheduled events) will show empty `LifeEventTimeline` + empty `ThoughtFeed`. The page should render without errors and show a non-judgmental empty state ("Nikita's world is just beginning…"), NOT a generic "no data" message.
- **Spec 110 dependency**: `pipeline_events` + life-sim outputs require Phase A pipeline-observability migration to be live. If the `pipeline_events` table is empty (e.g., fresh deployment), most timelines will be empty.
- **Push-notification deep-link target paths**: keep the URL shape (`/dashboard/nikita/{mind,circle,day,stories}`) STABLE — changing requires a migration plan for in-flight push registrations (Service Worker subscription URLs).

## Navigation

- Parent: [`portal/src/app/dashboard/`](../) (W7b will add dashboard/CLAUDE.md)
- Backend life-sim: [`nikita/life_simulation/`](../../../../../nikita/life_simulation/)
- Psyche agent: [`nikita/agents/psyche/agent.py`](../../../../../nikita/agents/psyche/agent.py)
- Pipeline observability spec: `specs/110-pipeline-observability-event-stream/`
- Memory canonical: [`memory/architecture.md`](../../../../../memory/architecture.md) §"Pydantic AI Agents" + §"11-Stage Async Pipeline"

Last verified: 2026-05-05
