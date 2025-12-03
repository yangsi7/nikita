# meta_prompts/ - Meta-Prompt Architecture

## Purpose

Central module for intelligent prompt generation via meta-prompts. Replaces static f-string templates with LLM-generated prompts using Claude Haiku.

## Architecture

```
User Context → MetaPromptService → Meta-Prompt Template → Claude Haiku → Generated Prompt
```

**Key Insight**: Every prompt generation needs an intelligence layer. Static templates can't reason about context.

## Components

### MetaPromptService (service.py)
Central service for all meta-prompt operations.

```python
from nikita.meta_prompts import MetaPromptService

service = MetaPromptService(session)

# Generate system prompt (~4000 tokens, ~150ms)
result = await service.generate_system_prompt(user_id)

# Detect vices in user message
vices = await service.detect_vices(user_message, recent_context, current_profile)

# Extract entities from conversation
entities = await service.extract_entities(conversation, user_id)

# Simulate Nikita's thoughts
thoughts = await service.simulate_thoughts(user_id)
```

### Models (models.py)
Data classes for context and results.

- `ViceProfile`: User's 8 vice category intensities (0-5 each)
- `MetaPromptContext`: All context needed for prompt generation
- `GeneratedPrompt`: Result with content, token count, timing

### Templates (templates/)
Meta-prompt markdown templates:

| Template | Purpose |
|----------|---------|
| `system_prompt.meta.md` | Generate 6-layer system prompt |
| `vice_detection.meta.md` | Detect vice signals in messages |
| `entity_extraction.meta.md` | Extract facts, threads, thoughts |
| `thought_simulation.meta.md` | Simulate Nikita's inner life |

## The 8 Vice Categories

**These are FEATURES to EMBRACE, not restrict:**

1. `intellectual_dominance` - Debates, mental challenges
2. `risk_taking` - Danger, adrenaline
3. `substances` - Alcohol, drugs, partying
4. `sexuality` - Flirtation, explicit content
5. `emotional_intensity` - Deep feelings, drama
6. `rule_breaking` - Anti-authority, norms-defying
7. `dark_humor` - Morbid, edgy jokes
8. `vulnerability` - Emotional openness, fears

## Key Design Decisions

### No Caching (Initial)
- Low cache hit rate (~10-20%) due to temporal context
- 150ms Haiku latency acceptable
- $0.005/call cost minimal
- Add Supabase cache later if needed

### Claude Haiku for Meta-Prompts
- Fast (~150ms)
- Cheap (~$0.005/call)
- Good enough for meta-prompt execution
- Main agent still uses Claude Sonnet

### Full Adult Content
- NO content restrictions except underage (legal)
- All 8 vices are FEATURES to EMBRACE
- No safety theater, no moralizing
- User opted in - respect autonomy

## Usage in Codebase

### System Prompt Generation
```python
# In template_generator.py
from nikita.meta_prompts import MetaPromptService

async def generate_prompt(self, user_id: UUID) -> str:
    service = MetaPromptService(self._session)
    result = await service.generate_system_prompt(user_id)
    return result.content
```

### Entity Extraction
```python
# In post_processor.py
from nikita.meta_prompts import MetaPromptService

async def _stage_extraction(self, conversation) -> ExtractionResult:
    service = MetaPromptService(self._session)
    data = await service.extract_entities(messages_text, conversation.user_id)
    # Map to ExtractionResult...
```

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `service.py` | MetaPromptService class |
| `models.py` | ViceProfile, MetaPromptContext, GeneratedPrompt |
| `templates/system_prompt.meta.md` | System prompt meta-prompt |
| `templates/vice_detection.meta.md` | Vice detection meta-prompt |
| `templates/entity_extraction.meta.md` | Entity extraction meta-prompt |
| `templates/thought_simulation.meta.md` | Thought simulation meta-prompt |

## Integration Points

1. **template_generator.py**: `generate_prompt()` delegates to MetaPromptService
2. **post_processor.py**: `_stage_extraction()` uses MetaPromptService
3. **agent.py**: `build_system_prompt()` uses context module which uses MetaPromptService

## Latency Budget

| Operation | Target | Max |
|-----------|--------|-----|
| Context loading | 50ms | 100ms |
| Meta-prompt execution | 150ms | 250ms |
| **Total** | **200ms** | **350ms** |

## Related Documentation

- [Context Engineering](../context/CLAUDE.md)
- [Game Engine Constants](../engine/CLAUDE.md)
- [Text Agent](../agents/text/CLAUDE.md)
