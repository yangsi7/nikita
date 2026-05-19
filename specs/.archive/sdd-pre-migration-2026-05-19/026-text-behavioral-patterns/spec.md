# Spec 026: Text Behavioral Patterns

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: 024
**Dependents**: None

---

## Overview

### Problem Statement

Current text responses lack realistic texting patterns. Real girlfriends:
1. Use emojis selectively (not constantly)
2. Vary message length based on context
3. Send multiple short messages vs one long one
4. Have consistent punctuation quirks

### Solution

Implement a **Text Behavioral Pattern System** that applies realistic texting patterns to Nikita's responses based on emotional state, context, and chapter.

---

## User Stories

### US-1: Emoji Usage
**As** Nikita,
**I want** to use emojis selectively and contextually,
**So that** my texting feels natural, not robotic.

**Priority**: P1

**Acceptance Criteria**:
- AC-1.1: Max 1-2 emojis per message, sometimes none
- AC-1.2: Classic emoticons allowed: :) :( :P ;)
- AC-1.3: Approved emoji set: 😏🙄🍆😘😅🥲🙂
- AC-1.4: Context-appropriate: flirtation, sarcasm, affection, self-deprecation
- AC-1.5: Never multiple emojis in sequence (no "😂😂😂")

### US-2: Message Length
**As** Nikita,
**I want** message length to match context,
**So that** my texting rhythm feels human.

**Priority**: P1

**Acceptance Criteria**:
- AC-2.1: Default: short, punchy messages (10-50 chars)
- AC-2.2: Emotional topics: longer messages (100-300 chars)
- AC-2.3: Fights/deep conversations: even longer
- AC-2.4: Never one-word responses unless intentional (conflict)

### US-3: Message Splitting
**As** Nikita,
**I want** to split long thoughts into multiple messages,
**So that** conversation feels like real texting.

**Priority**: P1

**Acceptance Criteria**:
- AC-3.1: Multiple short messages instead of one long paragraph
- AC-3.2: Natural break points (thought transitions)
- AC-3.3: Configurable split threshold (default 80 chars)
- AC-3.4: Timing between splits (50-200ms simulated)

### US-4: Punctuation Patterns
**As** Nikita,
**I want** consistent punctuation quirks,
**So that** my texting has personality.

**Priority**: P2

**Acceptance Criteria**:
- AC-4.1: Lowercase preference for casual messages
- AC-4.2: Occasional trailing dots "..." for effect
- AC-4.3: "lol" and "haha" usage patterns
- AC-4.4: Exclamation points used sparingly but genuinely

---

## Functional Requirements

### FR-001: Emoji Configuration

```python
class EmojiConfig(BaseModel):
    approved_emojis: list[str] = ["😏", "🙄", "🍆", "😘", "😅", "🥲", "🙂"]
    classic_emoticons: list[str] = [":)", ":(", ":P", ";)", ":/"]
    max_per_message: int = 2
    contexts: dict[str, list[str]] = {
        "flirtation": ["😏", "😘", "🍆", ";)"],
        "sarcasm": ["🙄", ":/"],
        "affection": ["🥲", "😘", ":)"],
        "self_deprecation": ["😅", "🥲"]
    }
```

### FR-002: Length Configuration

| Context | Min Chars | Max Chars | Splits |
|---------|-----------|-----------|--------|
| casual | 10 | 50 | 1-2 |
| flirty | 15 | 80 | 1-3 |
| emotional | 100 | 300 | 2-4 |
| conflict | 50 | 150 | 1-2 |
| deep | 150 | 400 | 3-5 |

### FR-003: Splitting Logic

```python
class MessageSplitter(BaseModel):
    split_threshold: int = 80
    min_split_length: int = 20
    split_markers: list[str] = ["but", "and", "also", "anyway", "so"]
    inter_message_delay_ms: tuple[int, int] = (50, 200)
```

---

## Technical Design

### File Structure

```
nikita/
├── text_patterns/
│   ├── __init__.py
│   ├── emoji_processor.py    # Emoji selection/validation
│   ├── length_adjuster.py    # Length based on context
│   ├── message_splitter.py   # Split into multiple messages
│   ├── punctuation.py        # Punctuation patterns
│   ├── models.py
│   └── processor.py          # TextPatternProcessor
├── config_data/
│   └── text_patterns/
│       ├── emojis.yaml
│       └── patterns.yaml
```

### Integration with 024

TextPatternProcessor is called AFTER MetaInstructionEngine applies behavioral nudges, applying final text formatting to the generated response.

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
- Initial specification
