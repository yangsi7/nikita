# engine/vice/ - Vice Personalization System

## Purpose

LLM-based vice detection, scoring, and prompt injection for personalized responses.

## Status: ✅ COMPLETE (70 tests)

Implemented: 2025-12-11

## Architecture

```
vice/
├── __init__.py      # Public API exports
├── models.py        # ViceSignal, ViceAnalysisResult, ViceProfile, ViceInjectionContext
├── analyzer.py      # ViceAnalyzer (LLM-based with Pydantic AI)
├── scorer.py        # ViceScorer (profile management)
├── injector.py      # VicePromptInjector (chapter-aware)
├── boundaries.py    # ViceBoundaryEnforcer (ethical limits)
└── service.py       # ViceService (high-level orchestration)
```

## 8 Vice Categories

| Category | Description |
|----------|-------------|
| intellectual_dominance | Enjoys intellectual challenges, debates, expertise |
| risk_taking | Attracted to danger, adventure, adrenaline |
| substances | Open discussion of alcohol, party culture |
| sexuality | Flirtation, attraction, romantic tension |
| emotional_intensity | Deep emotional exchanges, raw feelings |
| rule_breaking | Anti-authority, norm-defying perspectives |
| dark_humor | Morbid jokes, gallows humor |
| vulnerability | Emotional openness, sharing fears |

## Key Components

### ViceAnalyzer (analyzer.py)
- Uses Pydantic AI with Claude for structured output
- Detects vice signals from conversation exchanges
- Returns `ViceAnalysisResult` with confidence scores

```python
analyzer = ViceAnalyzer()
result = await analyzer.analyze_exchange(
    user_message="...",
    nikita_response="...",
    conversation_id=uuid
)
# result.signals: list[ViceSignal]
```

### ViceScorer (scorer.py)
- Processes signals to update intensity scores
- Manages user vice profiles via VicePreferenceRepository
- Supports profile retrieval and top vices filtering

```python
scorer = ViceScorer()
await scorer.process_signals(user_id, signals)
profile = await scorer.get_profile(user_id)
top_vices = await scorer.get_top_vices(user_id, n=3, min_threshold=0.3)
```

### VicePromptInjector (injector.py)
- Injects vice preferences into prompts
- Chapter-appropriate expression levels (subtle → explicit)
- Multi-vice blending with intensity-based prominence

```python
injector = VicePromptInjector()
modified_prompt = injector.inject(base_prompt, profile, chapter=3)
```

### ViceBoundaryEnforcer (boundaries.py)
- Caps sensitive categories by chapter
- sexuality, substances, rule_breaking have chapter-based limits
- Non-sensitive categories (dark_humor, etc.) are uncapped

```python
enforcer = ViceBoundaryEnforcer()
max_intensity = enforcer.max_intensity_for_chapter("sexuality", chapter=1)  # 0.35
capped = enforcer.apply_cap("sexuality", Decimal("0.95"), chapter=1)  # 0.35
```

### ViceService (service.py)
- High-level orchestration
- Combines analyzer, scorer, injector, and enforcer
- Handles discovery mode for new users

```python
service = ViceService()
context = await service.get_prompt_context(profile, chapter=3)
await service.process_conversation(user_id, user_msg, nikita_msg, conv_id)
probes = service.get_probe_categories(profile)
```

## Expression Levels by Chapter

| Chapter | Level | Style |
|---------|-------|-------|
| 1-2 | Subtle | Hints, mystery, guarded |
| 3 | Moderate | More open, comfortable |
| 4 | Direct | Openly embrace |
| 5 | Explicit | Fully authentic |

## Boundary Caps (Sensitive Categories)

| Category | Ch1 | Ch2 | Ch3 | Ch4 | Ch5 |
|----------|-----|-----|-----|-----|-----|
| sexuality | 0.35 | 0.45 | 0.60 | 0.75 | 0.85 |
| substances | 0.30 | 0.45 | 0.60 | 0.70 | 0.80 |
| rule_breaking | 0.40 | 0.55 | 0.70 | 0.80 | 0.90 |

## Tests

```bash
# Run all vice tests
pytest tests/engine/vice/ -v

# 70 tests total:
# - test_models.py: 17 tests
# - test_analyzer.py: 15 tests
# - test_scorer.py: 11 tests
# - test_injector.py: 14 tests
# - test_boundaries.py: 7 tests
# - test_service.py: 8 tests
```

## Remaining Work (T041, T043-T046)

- T041: Integrate ViceService into text agent
- T043: Verify 80%+ code coverage
- T044: Integration test: Full vice cycle
- T045: ✅ This documentation file
- T046: Update nikita/engine/CLAUDE.md status
