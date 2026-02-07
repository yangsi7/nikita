# ElevenLabs Console Setup Guide

This guide documents the ElevenLabs Conversational AI 2.0 configuration for Nikita voice agent.

## Agent Configuration

### Agent ID

The agent ID is stored in environment variables:
- `ELEVENLABS_DEFAULT_AGENT_ID` - Main Nikita agent for calls
- `ELEVENLABS_AGENT_META_NIKITA` - Meta-Nikita agent for onboarding

### System Prompt Variables

Dynamic variables are injected into the system prompt using `{{variable_name}}` syntax.

| Variable | Description | Source |
|----------|-------------|--------|
| `user_name` | User's name | Onboarding profile |
| `chapter` | Current chapter (1-5) | User.chapter |
| `relationship_score` | Score (0-100) | User.relationship_score |
| `engagement_state` | IN_ZONE, DRIFTING, etc. | Engagement model |
| `nikita_mood` | flirty, playful, etc. | Time-based |
| `nikita_energy` | low, moderate, high | Time-based |
| `time_of_day` | morning, afternoon, etc. | System time |
| `context_block` | Aggregated context | Built dynamically |

### Spec 032 Expanded Variables

| Variable | Description | Token Budget |
|----------|-------------|--------------|
| `today_summary` | Today's interactions | ~100 tokens |
| `last_conversation_summary` | Last conversation | ~100 tokens |
| `nikita_mood_arousal` | Emotional arousal (0-1) | N/A |
| `nikita_mood_valence` | Emotional valence (0-1) | N/A |
| `nikita_mood_dominance` | Emotional dominance (0-1) | N/A |
| `nikita_mood_intimacy` | Emotional intimacy (0-1) | N/A |
| `nikita_daily_events` | Life simulation events | ~100 tokens |
| `active_conflict_type` | Conflict type if any | ~20 tokens |
| `active_conflict_severity` | Conflict severity (0-1) | N/A |
| `emotional_context` | Mood summary | ~50 tokens |
| `user_backstory` | How they met | ~100 tokens |
| `context_block` | Full aggregated context | ~500 tokens |

## Server Tools Configuration

### Tool: get_context

**Description**: Load context about the user at the START of the call.

**WHEN TO USE**:
- Immediately at call start to understand who you're talking to
- After 10+ minutes if the call runs long (refresh context)

**Parameters**: None (user_id from signed token)

**Returns**: All dynamic variables for prompt injection

### Tool: get_memory

**Description**: Search your memory for past events, conversations, or facts about the user.

**WHEN TO USE**:
- User says "remember when..." or "didn't we..."
- User asks about something you should know from past conversations
- You want to reference a specific past event

**Parameters**:
- `query`: Search query string

**Returns**: Relevant memories and facts

### Tool: score_turn

**Description**: Score an emotional exchange to update the relationship.

**WHEN TO USE**:
- After meaningful emotional exchanges (confessions, arguments, flirting)
- When you feel the relationship dynamic changed
- NOT for casual conversation - only significant moments

**Parameters**:
- `user_message`: What the user said
- `nikita_message`: What you responded

**Returns**: Score deltas for intimacy, passion, trust, secureness

### Tool: update_memory

**Description**: Store a new fact about the user that you should remember.

**WHEN TO USE**:
- User shares NEW personal information (job, hobby, name, pet, etc.)
- You learn something important about them
- NOT for casual conversation details

**Parameters**:
- `fact`: The fact to store (e.g., "User's birthday is March 15")

## TTS Settings by Chapter

| Chapter | Stability | Similarity | Speed | Personality |
|---------|-----------|------------|-------|-------------|
| 1 | 0.75 | 0.65 | 0.95 | Reserved, cautious |
| 2 | 0.65 | 0.70 | 1.00 | Warming up |
| 3 | 0.55 | 0.80 | 1.05 | Playful, teasing |
| 4 | 0.50 | 0.85 | 1.05 | Affectionate |
| 5 | 0.45 | 0.90 | 1.10 | Passionate, intimate |

## Webhook Configuration

### Pre-Call Webhook

**URL**: `https://nikita-api-*.run.app/api/v1/voice/pre-call`

**Purpose**: Look up user by phone number, return availability

### Server Tool Webhook

**URL**: `https://nikita-api-*.run.app/api/v1/voice/server-tool`

**Purpose**: Handle server tool calls during conversation

### Post-Call Webhook

**URL**: `https://nikita-api-*.run.app/api/v1/voice/webhook`

**Events**:
- `call.connected` - Track call start
- `call.ended` - Store transcript, trigger post-processing

## Best Practices

### Tool Description Format

All tool descriptions follow WHEN/HOW/RETURNS/ERROR format:

```
WHEN TO USE: When to call this tool
HOW TO USE: Parameters and usage
RETURNS: What the tool returns
ERROR HANDLING: How to handle failures
```

### Context Block Usage

The `context_block` variable provides aggregated context in a single string:
- Relationship state and score
- Recent conversation summaries
- Emotional context
- Active conflicts

Use in prompt like: `Current context: {{context_block}}`

### Token Efficiency

- Total dynamic variables: ~500 tokens
- Refresh context every 10+ minutes on long calls
- Context block truncates to 2000 chars (~500 tokens)
