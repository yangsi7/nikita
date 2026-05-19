# Implementation Plan: 026 Text Behavioral Patterns

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Overview

Implement a Text Behavioral Pattern System that applies realistic texting patterns (emoji usage, message length, splitting, punctuation) to Nikita's responses.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  TEXT PATTERN PROCESSOR                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ EmojiProcessor  │    │ LengthAdjuster  │                     │
│  │ - select()      │    │ - adjust()      │                     │
│  │ - validate()    │    │ - truncate()    │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                    │
│  │         TextPatternProcessor            │                    │
│  │  - process()                            │                    │
│  │  - apply_patterns()                     │                    │
│  └─────────────────────────────────────────┘                    │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ MessageSplitter │    │ PunctuationProc │                     │
│  │ - split()       │    │ - apply()       │                     │
│  │ - find_breaks() │    │ - quirks()      │                     │
│  └─────────────────┘    └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```python
class TextPatternResult(BaseModel):
    original: str
    messages: list[str]  # Split messages
    emojis_added: list[str]
    length_adjusted: bool
    split_count: int
    delays_ms: list[int]  # Delays between messages
```

## Integration Points

| Component | Integration |
|-----------|-------------|
| 024 Meta-Instructions | Applies after behavioral nudges |
| Text Agent | Final processing before sending |
| Telegram | Multiple messages with delays |

## Implementation Phases

### Phase A: Core Infrastructure
- T001: Create text_patterns module
- T002: Implement models
- T003: Create config YAML files
- T004: Unit tests for models

### Phase B: Emoji Processing
- T005: Implement EmojiProcessor class
- T006: Implement context-based selection
- T007: Implement validation (max per message)
- T008: Unit tests for emoji processing

### Phase C: Length Adjustment
- T009: Implement LengthAdjuster class
- T010: Implement context-based length targets
- T011: Implement truncation with natural breaks
- T012: Unit tests for length adjustment

### Phase D: Message Splitting
- T013: Implement MessageSplitter class
- T014: Implement break point detection
- T015: Implement delay calculation
- T016: Unit tests for splitting

### Phase E: Punctuation
- T017: Implement PunctuationProcessor class
- T018: Implement quirk patterns
- T019: Unit tests for punctuation

### Phase F: Integration
- T020: Implement TextPatternProcessor
- T021: Wire to text agent
- T022: E2E tests
- T023: Quality tests

---

## Dependencies

### Upstream
- Spec 024: MetaInstructionEngine output

### Downstream
- None (terminal spec for text patterns)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Emoji density | 0.5-1.5 per 100 chars |
| Message split rate | 40% of responses split |
| User "feels natural" feedback | >70% |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan
