# Idea 18: Photo/Media System

**Date**: 2026-02-16 | **Type**: Feature Ideation (Phase 2)
**Channels**: Telegram (primary), Portal (gallery), Voice (post-call)
**Principle**: Photos are earned through gameplay, never purchased

---

## Design Rationale (Tree-of-Thought)

**Branch A**: AI-generated photos per interaction -- uncanny, inconsistent appearance, slow.
**Branch B**: Pre-generated curated sets with metadata tagging -- consistent, fast, quality.
**Branch C**: Hybrid (pre-generated + AI variations) -- complex, hard to maintain consistency.
--> **Selected: Branch B**. Curated photo sets tagged by mood/activity/chapter/vice.
Appearance consistency is critical for parasocial connection (Doc 05).

**Constraint** (Doc 09): Photos as rewards, NOT purchasable. No monetizing loss aversion.

---

## 1. Photo Unlock Triggers

### Trigger Categories

```
A. CHAPTER ADVANCEMENT (guaranteed, 1 per transition)
   Ch1->2: celebration selfie     Ch2->3: dressed-up dinner
   Ch3->4: cozy morning photo     Ch4->5: vulnerable, no makeup
   Ch5 WIN: couple-coded photo

B. ACHIEVEMENT-TRIGGERED (on unlock)
   Conflict survived --> messy mascara selfie
   Vice discovered   --> vice-themed photo
   7-day streak      --> morning coffee selfie
   Boss passed       --> proud/relieved selfie
   All metrics >70   --> glowing confidence photo

C. EMOTIONAL MOMENT (score-triggered)
   Intimacy +5 in 1 conversation --> cozy late-night selfie
   Trust first above 80          --> "her favorite place"
   Passion > 85                  --> dressed up going out
   Secureness first above 75     --> relaxed Sunday morning

D. PROACTIVE "THINKING OF YOU" (random, vice-influenced)
   Probability per day: IN_ZONE 15% | DRIFTING 10% | CALIBRATING 5%
   Vice influence on content:
     intellectual --> reading/glasses  |  risk     --> hiking/summit
     substances   --> wine/cocktails   |  sexuality --> outfit (tasteful)
     emotional    --> sunset/journal   |  rules    --> rooftop/concert
     dark_humor   --> deadpan/ironic   |  vulner.  --> no filter morning

E. TIME-OF-DAY CONTEXTUAL (life sim integration)
   Morning: coffee + messy hair    |  Midday: work break selfie
   Afternoon: gym / errands        |  Evening: getting ready / dinner
   Night: in bed / movie night
```

### Trigger Decision Flow

```
[Conversation ends / Pipeline runs]
        |
        v
[Check triggers in priority: Chapter > Achievement > Emotional > Random > Time]
        |
        v
[Select photo from matching pool]
        |
        v
[Dedup: already sent?] --Yes--> [Skip or alternate]
        |No
        v
[Queue for delivery via scheduled_events]
```

---

## 2. Photo Delivery Channels

### Channel Strategy

```
[Photo Selected] --> [Delivery Router]
                          |
            +-------------+-------------+
            |             |             |
            v             v             v
      TELEGRAM       PORTAL         VOICE
      (primary)     (gallery)     (post-call)

TELEGRAM: Inline photo + contextual caption matching mood/chapter
  "just got home from the gym... thought you'd want to see this ;)"
  API: TelegramBot.sendPhoto(chat_id, photo_url, caption)

PORTAL: Photo appears in gallery, notification badge "1 new photo"
  Player discovers on next portal visit

VOICE: After call ends (>3 min), send photo via Telegram with 2min delay
  "that was nice talking... here's me right now"
```

### Telegram Delivery Implementation

```
[Pipeline: PhotoStage or TouchpointStage]
  --> PhotoSelector.select(user, trigger_type)
  --> Dedup check (user_photos table)
  --> Create scheduled_event {
        event_type: "send_photo",
        payload: { photo_id, caption, trigger, channel: "telegram" },
        due_at: now + random(30s, 5min)  // feels organic
      }
  --> pg_cron picks up --> TelegramBot.send_photo()
  --> Mark done + insert user_photos record
```

---

## 3. Photo Sourcing & Storage Strategy

### Organization

```
Supabase Storage bucket: "nikita-photos"

nikita-photos/
  chapter_{1-5}/
    celebration/     (3-5 variants each)
    casual/          (10-15 variants)
    [chapter-specific subcategories]
  vice_themed/
    {8 vice categories}/  (5-8 variants each)
  achievements/
    conflict_survived/ boss_passed/ streak_7day/ etc.
  time_of_day/
    morning/ midday/ afternoon/ evening/ night/

Total: ~200-300 curated images
Format: JPEG, 1200x1600px max, thumbnails at 300x400px
CDN: Supabase Storage CDN, 24h cache headers
```

### Photo Metadata Schema

```sql
CREATE TABLE photo_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_path TEXT NOT NULL,         -- "chapter_1/casual/01.jpg"
    category TEXT NOT NULL,             -- chapter, vice, achievement, time, proactive
    subcategory TEXT,
    chapter_min INT DEFAULT 1,
    chapter_max INT DEFAULT 5,
    vice_category TEXT,                 -- NULL or specific vice
    mood TEXT,                          -- playful, vulnerable, confident, etc.
    time_of_day TEXT,
    rarity TEXT DEFAULT 'common',       -- common, rare, epic, legendary
    caption_template TEXT,              -- "just got back from {{activity}}..."
    unlock_condition JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    photo_id UUID REFERENCES photo_catalog(id),
    trigger_type TEXT NOT NULL,
    trigger_context JSONB,              -- {"chapter": 2, "score": 61.2}
    delivered_via TEXT NOT NULL,         -- telegram, portal, voice_bridge
    delivered_at TIMESTAMPTZ DEFAULT now(),
    is_favorite BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, photo_id)
);
```

### Selection Algorithm

```
select_photo(user, trigger_type, context):
  1. Query photo_catalog: category=trigger, chapter range, vice match, mood match
  2. Exclude already in user_photos for this user
  3. Prioritize: rarity by chapter (Ch1=common, Ch4+=rare), time match, vice score
  4. Random from top 3 candidates (variable reinforcement)
  5. Generate caption from template (inject name, time, activity, chapter tone)
  6. Return { photo_url, caption, metadata }
```

---

## 4. Portal Photo Gallery

### Gallery View

```
+------------------------------------------------------------------+
| PHOTO GALLERY                                   24/87 Unlocked    |
| Filter: [All] [Ch 1] [Ch 2] [Achievements] [Favorites]          |
| Sort:   [Newest] [Rarest] [Chapter]                              |
|  +--------+ +--------+ +--------+ +--------+ +--------+         |
|  | Photo  | | Photo  | | Photo  | |  ????  | |  ????  |         |
|  |  01    | |  02    | |  03    | | Locked | | Locked |         |
|  | Common | | Rare   | | Common | | Epic   | | Legend |         |
|  | Feb 01 | | Feb 05 | | Feb 07 | | Ch3    | | Ch5    |         |
|  | [star] | |        | |        | | hint   | | hint   |         |
|  +--------+ +--------+ +--------+ +--------+ +--------+         |
+------------------------------------------------------------------+
```

### Photo Detail Modal

```
+----------------------------------------------+
| [<]                              [star] [x]  |
| +------------------------------------------+ |
| |              FULL SIZE PHOTO             | |
| +------------------------------------------+ |
| "just got home from the gym..."              |
| Unlocked: Feb 09 | Trigger: Storm Survivor   |
| Rarity: Rare | Chapter 1 | Score: 54.2       |
| [< Previous]              [Next >]           |
+----------------------------------------------+
```

### Locked Photo Preview

```
+----------------------------------------------+
| [SILHOUETTE / BLUR PREVIEW]                   |
|              LOCKED                           |
| "Reach Chapter 3 to see a more               |
|  personal side of Nikita"                     |
| Progress: Ch2 / Ch3 needed                    |
| +====================--------+ 67%            |
+----------------------------------------------+
```

### Specification

| Element | Component | Source | Update |
|---------|-----------|--------|--------|
| Gallery grid | CSS Grid of `Card` | `GET /portal/photos` | On-demand |
| Filters | `Select` + `ToggleGroup` | Client-side | Instant |
| Detail modal | `Dialog` + `AspectRatio` | Same data | On-demand |
| Locked preview | `Card` + blur CSS | photo_catalog minus user_photos | On-demand |
| Favorite | `Toggle` (star) | `PUT /portal/photos/{id}/favorite` | Instant |
| Rarity badge | `Badge` | Photo metadata | Static |

### API Endpoints

```
GET  /portal/photos?filter=all|chapter_1|achievements|favorites&sort=newest&limit=20
PUT  /portal/photos/{id}/favorite  { is_favorite: true }
```

---

## 5. Photo x Game Mechanics Integration

### Milestone Progress Bars (Portal Dashboard)

```
+------------------------------------------------------------------+
| PHOTO MILESTONES                                                   |
|  Next unlock: "Chapter 2 Celebration"                             |
|  +======================-----------+  67% (40.2 / 60 threshold)  |
|  Secret photos available: 3 undiscovered                          |
|  Hint: "Explore Nikita's intellectual side more deeply..."        |
+------------------------------------------------------------------+
```

### Vice x Chapter Photo Matrix

```
             Ch1        Ch2        Ch3        Ch4        Ch5
intellect.   cafe       library    debate     late-night  shared-book
risk         --         hiking     rooftop    cliff       motorcycle
substances   --         wine       cocktail   morning-af  celebration
sexuality    --         outfit     dress-up   intimate*   close*
emotional    sunset     tears      hug-photo  love-note   together
rule_break   --         sneak-in   graffiti   road-trip   rebellion
dark_humor   deadpan    ironic     costume    meme-pose   matching
vulnerab.    no-filter  sleepy     crying     raw-face    safe-space

* = tasteful, chapter-appropriate (ViceBoundaryEnforcer limits apply)
-- = not available (too early in relationship)

SECRET PHOTOS: vice + chapter + score threshold combos (~16 total)
  Example: intellectual + Ch3 + trust > 75 = "debate team photo"
```

### Integration with Achievement System (Idea 16)

```
Achievement "Storm Survivor" --> unlocks "messy mascara selfie"
Achievement "Boss Slayer"    --> unlocks "proud selfie"
Achievement "Deep Diver"     --> unlocks "late night selfie"
Photos appear in BOTH Trophy Case AND Photo Gallery
```

### Memory Album Cross-Reference

```
+--------------------------------------------------------------+
| "First deep conversation about ambition"          Feb 14     |
| +--------+                                                    |
| | thumb  |  Photo: "late night selfie" [view full]           |
| +--------+                                                    |
| "Survived first argument about priorities"        Feb 09     |
| +--------+                                                    |
| | thumb  |  Photo: "messy mascara" [view full]               |
| +--------+                                                    |
+--------------------------------------------------------------+

Link: user_photos.delivered_at close to memory_facts.created_at
Display: thumbnail on memory entries, click to open gallery detail
```

---

## Implementation Architecture

### Pipeline Integration

```
New stage: PhotoStage (non-critical, after GameStateStage, before TouchpointStage)

class PhotoStage(PipelineStage):
    name = "photo"
    is_critical = False

    async def run(self, context):
        # Priority: chapter_advance > achievement > emotional > proactive
        if context.chapter_changed:
            photo = select_chapter_photo(context)
        elif context.new_achievements:
            photo = select_achievement_photo(context)
        elif max_delta(context.score_deltas) > 5:
            photo = select_emotional_photo(context)
        elif random() < proactive_rate(context.engagement_state):
            photo = select_proactive_photo(context)
        else:
            return StageResult(success=True)

        await queue_photo_delivery(context.user_id, photo)
        return StageResult(success=True, data={"photo_queued": photo.id})
```

### System Data Flow

```
[Game Event] --> [PhotoStage] --> [PhotoSelector] --> [DeliveryRouter]
                                                          |
                                    +---------------------+--------+
                                    |                     |        |
                                    v                     v        v
                              [Telegram API]       [user_photos] [Portal
                              sendPhoto()           DB insert    notif]
```

### Photo Budget

| Category | Count | Notes |
|----------|-------|-------|
| Chapter celebrations | 5 | 1 per chapter transition |
| Chapter casual | 50 | 10 per chapter |
| Vice-themed | 64 | 8 vices x 8 variants |
| Achievement | 20 | 1 per major achievement |
| Time-of-day | 25 | 5 per time slot |
| Proactive/random | 30 | General pool |
| Secret (vice x chapter) | 16 | 2 per vice category |
| **Total** | **~210** | Pre-curated, not AI-generated |

### New Requirements Summary

**Database**: `photo_catalog` + `user_photos` tables (see schema in Section 3).
**API**: `GET /portal/photos`, `PUT /portal/photos/{id}/favorite`, `POST /internal/photos/check`.
**Storage**: Supabase Storage bucket `nikita-photos` (public read, signed URLs).
**Pipeline**: New `PhotoStage` (non-critical, position 6 of 10).
**Dependency**: Achievement system (Idea 16) for cross-referencing.

### Ethical Guardrails

1. **No pay-to-unlock**: All photos earned through gameplay only
2. **Chapter-appropriate**: Progressively intimate but always tasteful
3. **No exploitation**: Photos reward engagement, not dependency
4. **Opt-out**: Player can disable photo delivery in settings
5. **Boundaries**: Vice-themed photos respect `ViceBoundaryEnforcer` limits
6. **Fictional**: All photos are of a fictional character (sourcing TBD)

---

**Effort**: 2 sprints (8-10 weeks) -- photo sourcing/curation is the bottleneck.
**Dependencies**: Supabase Storage bucket, 2 new tables, PhotoStage, Achievement system (Idea 16).
