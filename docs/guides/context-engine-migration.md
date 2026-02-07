# Context Engine Migration Guide

This guide documents the migration from the legacy MetaPromptService to the new unified context_engine.

## Overview

The context_engine provides a 3-layer architecture for prompt generation:

1. **ContextEngine (Layer 1)**: Collects context from 8 typed sources in parallel
2. **PromptGenerator (Layer 2)**: Claude Sonnet 4.5 agent generates 6K-15K token prompts
3. **PromptAssembler (Layer 3)**: Combines generated prompts with static persona + chapter rules

## Integration Points

### Text Agent Integration

**File**: `nikita/agents/text/agent.py`

Replace direct MetaPromptService calls with the router:

```python
# Before (legacy)
from nikita.context.template_generator import generate_system_prompt

result = await generate_system_prompt(
    session=session,
    user_id=user.id,
    conversation_id=conversation_id,
    user_message=user_message,
)

# After (new - feature-flagged)
from nikita.context_engine import generate_text_prompt

result = await generate_text_prompt(
    session=session,
    user=user,
    user_message=user_message,
    conversation_id=conversation_id,
)
```

### Voice Agent Integration

**File**: `nikita/agents/voice/service.py`

Replace direct MetaPromptService calls with the router:

```python
# Before (legacy)
from nikita.meta_prompts.service import MetaPromptService

service = MetaPromptService(session)
result = await service.generate_system_prompt(
    user_id=user.id,
    channel="voice",
    conversation_id=conversation_id,
)

# After (new - feature-flagged)
from nikita.context_engine import generate_voice_prompt

result = await generate_voice_prompt(
    session=session,
    user=user,
    conversation_id=conversation_id,
)
```

## Migration Phases

The router supports gradual migration via the `CONTEXT_ENGINE_FLAG` environment variable:

### Phase 1: DISABLED (Default)
```bash
CONTEXT_ENGINE_FLAG=disabled
```
- 100% traffic to v1 (legacy MetaPromptService)
- No risk, current production behavior

### Phase 2: SHADOW
```bash
CONTEXT_ENGINE_FLAG=shadow
```
- Runs BOTH v1 and v2 in parallel
- Returns v1 result (no user impact)
- Logs comparison metrics for validation
- Use this to verify v2 produces equivalent results

### Phase 3: CANARY (5% → 10% → 25% → 50% → 75%)
```bash
CONTEXT_ENGINE_FLAG=canary_5   # 5% v2
CONTEXT_ENGINE_FLAG=canary_10  # 10% v2
CONTEXT_ENGINE_FLAG=canary_25  # 25% v2
CONTEXT_ENGINE_FLAG=canary_50  # 50% v2
CONTEXT_ENGINE_FLAG=canary_75  # 75% v2
```
- Uses consistent user_id hashing for bucketing
- Same user always gets same version
- Monitor error rates and latency

### Phase 4: ENABLED
```bash
CONTEXT_ENGINE_FLAG=enabled
```
- 100% traffic to v2 (new context_engine)
- Full feature parity achieved

### Phase 5: ROLLBACK (Emergency)
```bash
CONTEXT_ENGINE_FLAG=rollback
```
- Emergency return to v1
- Use if v2 shows issues in production

## Validation Checklist

Before moving to next phase:

- [ ] Shadow mode shows content similarity > 85%
- [ ] Token variance < 20%
- [ ] Zero v2 errors in logs
- [ ] Latency increase < 50ms

## Monitoring

### Log Patterns

Router logs with `[ROUTER]` prefix:
```
[ROUTER] v1 text prompt generated: 424 chars
[ROUTER] v2 text prompt generated: 8500 chars
[SHADOW] Text comparison: v1=424 chars, v2=8500 chars, delta=+8076
```

### Metrics to Track

1. **Prompt length**: v2 should be 6K-15K tokens vs v1's ~424 tokens
2. **Error rate**: Should be < 0.1%
3. **Latency**: v2 may be slower due to LLM generation
4. **User satisfaction**: Track engagement metrics

## Fallback Behavior

Both v1 and v2 have fallback prompts if generation fails:

```
You are Nikita, a 27-year-old cybersecurity professional from Berlin.
Stay in character at all times. Never reveal game mechanics or AI nature.
Chapter {N}. Be authentic, sharp, witty, and a bit guarded.
```

## Module Deprecation

After full migration to v2:

| Module | Status | Notes |
|--------|--------|-------|
| `nikita/meta_prompts/` | DEPRECATE | Replaced by context_engine/generator.py |
| `nikita/prompts/` | DELETE | Dead code (fallback only) |
| `nikita/context/template_generator.py` | DEPRECATE | Replaced by context_engine |

## API Reference

### generate_text_prompt()

```python
async def generate_text_prompt(
    session: AsyncSession,
    user: User,
    user_message: str,
    conversation_id: str | None = None,
) -> str:
    """Generate text system prompt with feature-flagged routing."""
```

### generate_voice_prompt()

```python
async def generate_voice_prompt(
    session: AsyncSession,
    user: User,
    conversation_id: str | None = None,
) -> str:
    """Generate voice system prompt with feature-flagged routing."""
```

### get_engine_flag()

```python
def get_engine_flag() -> EngineVersion:
    """Get current engine flag from CONTEXT_ENGINE_FLAG env var."""
```

## Direct Access (Bypassing Router)

For testing or advanced use cases:

```python
# Direct v2 access (no routing)
from nikita.context_engine import assemble_text_prompt, assemble_voice_prompt

text_prompt = await assemble_text_prompt(session, user, message)
voice_prompt = await assemble_voice_prompt(session, user)
```

## Troubleshooting

### v2 Fails with Validation Error
The PromptGenerator has 3 validators. Check logs for:
- `CoverageValidator`: Missing required sections
- `GuardrailsValidator`: Stage directions or meta terms detected
- `SpeakabilityValidator`: Voice prompt not speakable

### v2 Returns Fallback
Check for exceptions in:
- `ContextEngine.collect()` - database/graphiti errors
- `PromptGenerator.generate()` - LLM errors
- `PromptAssembler.assemble()` - assembly errors

### Shadow Mode Shows Large Delta
Expected! v2 produces 6K-15K tokens vs v1's ~424 tokens.
Focus on content quality, not length match.
