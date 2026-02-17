# Infrastructure Discovery: Monitoring-Relevant Database

**Date**: 2026-01-22
**Type**: Discovery
**Scope**: nikita/db/models/, nikita/db/repositories/

---

## Entity Relationship Diagram

```
                                    +------------------+
                                    |      users       |
                                    +------------------+
                                    | id (PK, UUID)    |
                                    | telegram_id      |
                                    | phone            |
                                    | relationship_score
                                    | chapter          |
                                    | game_status      |
                                    | onboarding_status|
                                    | cached_voice_*   |
                                    +--------+---------+
                                             |
         +-----------------------------------+-----------------------------------+
         |                |                  |                  |                |
         v                v                  v                  v                v
+----------------+ +----------------+ +----------------+ +----------------+ +----------------+
|  user_metrics  | | conversations  | | score_history  | | daily_summaries| |engagement_state|
+----------------+ +----------------+ +----------------+ +----------------+ +----------------+
| user_id (FK)   | | user_id (FK)   | | user_id (FK)   | | user_id (FK)   | | user_id (FK)   |
| intimacy       | | platform       | | score          | | date           | | state          |
| passion        | | messages (JSONB)| chapter        | | score_start/end| | multiplier     |
| trust          | | status         | | event_type     | | summary_text   | | calibration    |
| secureness     | | processing_*   | | event_details  | | key_moments    | +----------------+
+----------------+ +----------------+ +----------------+ +----------------+
                           |
         +-----------------+------------------+------------------+
         |                 |                  |                  |
         v                 v                  v                  v
+------------------+ +------------------+ +------------------+ +------------------+
| generated_prompts| | conv_threads     | | nikita_thoughts  | | message_embeddings|
+------------------+ +------------------+ +------------------+ +------------------+
| user_id (FK)     | | user_id (FK)     | | user_id (FK)     | | user_id (FK)     |
| conversation_id  | | thread_type      | | thought_type     | | conversation_id  |
| prompt_content   | | content          | | content          | | embedding (Vector)|
| token_count      | | status           | | expires_at       | +------------------+
| context_snapshot | +------------------+ | used_at          |
+------------------+                      +------------------+

+------------------+
| job_executions   |  (No FK - standalone)
+------------------+
| job_name         |
| status           |
| started_at       |
| completed_at     |
| duration_ms      |
| result (JSONB)   |
+------------------+
```

---

## Tables Relevant to Monitoring

### 1. users (user.py:36-199)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| id | UUID | User lookup |
| telegram_id | BigInt | Platform correlation |
| phone | String(20) | Voice correlation |
| relationship_score | Decimal(5,2) | Game state tracking |
| chapter | Int | Progress tracking |
| game_status | String(20) | active/boss_fight/game_over/won |
| onboarding_status | String(20) | pending/in_progress/completed/skipped |
| last_interaction_at | DateTime | Activity tracking |
| cached_voice_prompt | Text | Voice cache state |

### 2. conversations (conversation.py:31-155)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| id | UUID | Conversation lookup |
| user_id | FK(users) | User correlation |
| platform | String(20) | telegram/voice |
| messages | JSONB | Message history |
| status | Text | active/processing/processed/failed |
| processing_attempts | Int | Retry tracking |
| processing_started_at | DateTime | Stuck detection |
| score_delta | Decimal(5,2) | Impact tracking |
| conversation_summary | Text | Post-processing output |

### 3. generated_prompts (generated_prompt.py:19-63)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| id | UUID | Prompt lookup |
| user_id | FK(users) | User correlation |
| conversation_id | FK(conversations) | Context correlation |
| prompt_content | Text | Actual prompt text |
| token_count | Int | Token usage monitoring |
| generation_time_ms | Float | Performance monitoring |
| meta_prompt_template | String(100) | Template tracking |
| context_snapshot | JSONB | Debug context |
| created_at | DateTime | Timeline |

### 4. score_history (game.py:19-65)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| id | UUID | Event lookup |
| user_id | FK(users) | User correlation |
| score | Decimal(5,2) | Score snapshot |
| chapter | Int | Chapter at event |
| event_type | String(50) | conversation/decay/boss_pass/boss_fail |
| event_details | JSONB | Event context |
| recorded_at | DateTime | Event timeline |

### 5. job_executions (job_execution.py:37-82)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| id | UUID | Execution lookup |
| job_name | String(50) | decay/deliver/summary/cleanup/process-conversations |
| status | String(20) | running/completed/failed |
| started_at | DateTime | Execution start |
| completed_at | DateTime | Execution end |
| duration_ms | Int | Performance tracking |
| result | JSONB | Execution metrics |

### 6. daily_summaries (game.py:69-128)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| date | Date | Day tracking |
| score_start/end | Decimal(5,2) | Daily score delta |
| conversations_count | Int | Activity volume |
| summary_text | Text | Generated summary |
| key_moments | JSONB | Significant events |
| emotional_tone | Text | positive/neutral/negative |

### 7. conversation_threads (context.py:61-120)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| thread_type | Text | unresolved/cliffhanger/promise/curiosity/callback |
| status | Text | open/resolved/expired |
| content | Text | Thread content |

### 8. nikita_thoughts (context.py:123-191)
| Column | Type | Monitoring Use |
|--------|------|----------------|
| thought_type | Text | worry/curiosity/anticipation/reflection/desire |
| used_at | DateTime | Thought lifecycle |
| expires_at | DateTime | Thought validity |

---

## Repository Methods for Monitoring

### ConversationRepository (conversation_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get_recent(user_id, limit)` | 141-162 | Recent conversations |
| `get_stale_active_conversations()` | 228-257 | Detect stale for processing |
| `detect_stuck(timeout_minutes)` | 287-313 | Find stuck processing |
| `get_processed_conversations()` | 466-494 | Processed for summary |
| `get_active_conversation(user_id)` | 443-464 | Current active session |

### UserRepository (user_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get(user_id)` | 39-58 | User with metrics loaded |
| `get_by_telegram_id()` | 60-75 | Telegram lookup |
| `get_by_phone_number()` | 77-101 | Voice lookup |
| `get_active_users_for_decay()` | 311-326 | Decay candidates |

### GeneratedPromptRepository (generated_prompt_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get_by_user_id(limit)` | 64-83 | Recent prompts for user |
| `get_recent_by_user_id()` | 106-129 | Admin debugging |
| `get_latest_by_user_id()` | 131-147 | Most recent prompt |

### ScoreHistoryRepository (score_history_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get_history(user_id, limit)` | 59-80 | Score timeline |
| `get_daily_stats(target_date)` | 82-133 | Daily aggregation |
| `get_events_by_type(event_type)` | 135-159 | Filter by event type |
| `get_history_since(since)` | 161-185 | Time-range query |

### JobExecutionRepository (job_execution_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get_latest_by_job_name()` | 26-42 | Latest execution per job |
| `get_recent_executions(job_name, status)` | 44-69 | Filtered execution list |
| `start_execution(job_name)` | 71-88 | Start tracking |
| `complete_execution()` | 90-121 | Mark complete |
| `fail_execution()` | 123-154 | Mark failed |

### DailySummaryRepository (summary_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get_by_date(summary_date)` | 81-101 | Specific date summary |
| `get_range(start_date, end_date)` | 103-127 | Date range query |
| `get_recent(limit)` | 201-222 | Recent summaries |

### EngagementStateRepository (engagement_repository.py)
| Method | Line | Purpose |
|--------|------|---------|
| `get_by_user_id()` | 26-37 | Current engagement state |
| `get_recent_transitions()` | 39-58 | State change history |

---

## Data Gaps for Monitoring

### Currently NOT Queryable

1. **Cross-user aggregations** - No methods for system-wide stats
   - Total active users
   - Conversations per day (all users)
   - Average processing time

2. **Real-time metrics** - No streaming/websocket support
   - Live conversation count
   - Current processing queue depth

3. **Voice-specific queries** - Limited voice filtering
   - No `get_voice_conversations()` method
   - No ElevenLabs session correlation queries

4. **Token budget tracking** - No historical queries
   - No `get_token_usage_by_date()` method
   - No context_snapshot aggregation

5. **Processing pipeline observability**
   - No `get_failed_by_stage()` method
   - No retry success rate tracking

### Indexes (from model definitions)

**Indexed columns** (job_execution.py:51):
- `job_executions.job_name` - indexed for filtering

**Missing indexes** (potential performance issues):
- `conversations.status` - frequently filtered
- `conversations.platform` - voice/telegram filtering
- `conversations.user_id + status` - composite
- `generated_prompts.created_at` - timeline queries
- `score_history.recorded_at` - timeline queries

---

## Cascade Delete Chain

From `user_repository.py:649-679`:
```
User deletion cascades to:
- user_metrics
- user_vice_preferences
- conversations
- score_history
- daily_summaries
- conversation_threads
- nikita_thoughts
- engagement_state, engagement_history
- generated_prompts
- profile, backstory
- scheduled_events, scheduled_touchpoints
```

---

## Summary

**16 model files** define the schema across 4 domains:
1. **User Domain**: users, user_metrics, user_vice_preferences, profile, backstory
2. **Conversation Domain**: conversations, message_embeddings, conversation_threads, nikita_thoughts
3. **Game Domain**: score_history, daily_summaries, engagement_state, engagement_history
4. **System Domain**: job_executions, generated_prompts, pending_registration

**17 repository files** provide query methods with good coverage for:
- User lookup and state management
- Conversation lifecycle and processing
- Score history and daily summaries
- Job execution tracking

**Gaps identified**:
- No system-wide aggregation queries
- No voice-specific filtering
- Missing indexes on frequently-filtered columns
- No token budget historical tracking
