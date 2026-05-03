# Deep Audit Report: Nikita Context & Memory Gaps

**Date**: 2026-01-15
**Auditor**: Claude Code (4 parallel audit agents)
**Status**: COMPLETE - Remediation Spec Created (029)

---

## Executive Summary

A comprehensive deep audit of Nikita's game implementation vs specifications revealed **3 critical gaps** preventing Nikita from feeling like a real girlfriend:

| Gap | Severity | Impact | Remediation |
|-----|----------|--------|-------------|
| Memory Flow | P0 | 67% of graphs unused | Spec 029 Phase A |
| Humanization Wiring | P0 | 87.5% of modules unwired | Spec 029 Phase B |
| Voice-Text Parity | P1 | 85% context missing | Spec 029 Phase D |

**Root Cause**: Implementation divergence - NEW modules exist with passing tests but OLD pipeline still active in production.

---

## Gap 1: Memory Flow (P0 - Critical)

### Problem
2 of 3 knowledge graphs are stored but NEVER retrieved into prompts.

### Evidence
```python
# nikita/meta_prompts/service.py:296
async def get_user_facts(self, user_id: str) -> list[str]:
    # BUG: Only queries user_graph, ignoring relationship and nikita graphs
    return await self.memory.search_memory(query, graph_types=["user"])
```

### Impact
- **Relationship graph**: Inside jokes, significant moments, conflicts - NEVER appear in prompts
- **Nikita graph**: Her daily activities, mood, life events - NEVER appear in prompts
- **User perception**: Nikita feels like she has amnesia, doesn't remember shared history

### Current vs Required

| Metric | Current | Required |
|--------|---------|----------|
| Graphs queried | 1 (user) | 3 (user + relationship + nikita) |
| User facts loaded | 5 | 50+ |
| Relationship episodes | 0 | 10+ |
| Nikita life events | 0 | 10+ |

### Fix
Modify `service.py:296` to query all 3 graphs:
```python
facts = await self.memory.search_memory(
    query,
    graph_types=["user", "relationship", "nikita"],
    limit=50
)
```

---

## Gap 2: Humanization Pipeline Disconnected (P0 - Critical)

### Problem
7 of 8 humanization specs (021-027) have working code but are NEVER called from production.

### Evidence

| Spec | Module | Tests | Production |
|------|--------|-------|------------|
| 021 | `nikita/context/composer.py` | 345 ✅ | ❌ NOT CALLED |
| 022 | `nikita/life_simulation/` | 212 ✅ | ❌ NOT CALLED |
| 023 | `nikita/emotional_state/` | 233 ✅ | ❌ NOT CALLED |
| 024 | `nikita/behavioral/` | 166 ✅ | ❌ NOT CALLED |
| 025 | `nikita/touchpoints/` | 189 ✅ | ❌ NOT CALLED |
| 026 | `nikita/text_patterns/` | 167 ✅ | ❌ NOT CALLED |
| 027 | `nikita/conflicts/` | 263 ✅ | ❌ NOT CALLED |
| 028 | `nikita/onboarding/` | 230 ✅ | ✅ WORKING |

**Total**: 1575 tests passing, but modules never invoked.

### Root Cause
Two parallel pipelines exist:
- **OLD**: `nikita/context/post_processor.py` - ACTIVE in production
- **NEW**: `nikita/post_processing/` - NEVER called

```python
# nikita/api/routes/tasks.py (CURRENT - OLD pipeline)
from nikita.context.post_processor import PostProcessor

# SHOULD BE (NEW pipeline)
from nikita.post_processing import PostProcessingPipeline
```

### Impact
- **Life simulation**: Nikita has no daily life (events never generated)
- **Emotional state**: 4D mood never influences responses
- **Behavioral patterns**: No adaptive response styles
- **Conflicts**: No realistic relationship tension
- **Touchpoints**: Nikita never initiates messages

### Fix
Replace import in `tasks.py` and wire all 7 modules into message handler.

---

## Gap 3: Voice-Text Parity (P1 - High)

### Problem
Voice agent receives 85% less context than text agent.

### Evidence

**Text Agent Context** (`MetaPromptService.get_context()`):
```python
{
    "user_facts": [...],        # 20+ items
    "active_threads": [...],    # 3+ threads
    "today_summary": "...",
    "week_summaries": [...],
    "thoughts": [...],
    "backstory": "...",
    "secureness": 0.75,
    "vice_profile": {...},      # All 8 categories
    "hours_since_last": 4.5,
    "engagement_state": "IN_ZONE"
}
```

**Voice Agent Context** (`server_tools.py get_context()`):
```python
{
    "user_facts": [...],        # Only 3 items
    "chapter": 1,
    "scores": {...}
    # Missing: secureness, vice_profile, threads, summaries, etc.
}
```

### Impact
- Voice conversations feel less personalized
- Nikita doesn't reference past conversations in voice
- Different personality in voice vs text

### Fix
Expand server tools to return all context fields matching text agent.

---

## Gap 4: Token Budget Insufficient (P1 - High)

### Problem
Current prompts ~4,000 tokens vs user requirement of 10,000+ tokens.

### Current Token Distribution

| Layer | Current | Target |
|-------|---------|--------|
| L1: Base Persona | 400 | 800 |
| L2: Chapter | 300 | 600 |
| L3: Emotional | 200 | 500 |
| L4: Situational | 200 | 400 |
| L5: Context | 1,800 | 6,000 |
| L6: On-the-fly | 300 | 700 |
| **Total** | ~4,000 | **10,000+** |

### Impact
- Insufficient context for deep personalization
- Memory limited to 5 facts (should be 50+)
- No room for relationship history

### Fix
Expand all layer templates and increase context limits.

---

## External Research Findings

### AI Companion Memory Best Practices (18 sources, 88% confidence)

| Pattern | Recommendation | Our Status |
|---------|----------------|------------|
| Token Budget | 10,000+ for relationships | ❌ Only 4,000 |
| Memory Tiers | Critical / Recent / Historical | ❌ All loaded equally |
| Graph Integration | All relationship data in context | ❌ 1/3 graphs used |
| Lazy Loading | 62% cost reduction possible | ❌ Not implemented |
| Caching | 30-40% speedup | ❌ Not implemented |

### Key Research Insight
> "The most successful AI companions use 3-tier memory injection: always-loaded (profile, current state), recent (last 7 days), and on-demand (historical). This reduces cold-path tokens by 62% while maintaining relationship depth."

---

## Remediation Plan

### Created: Spec 029 - Comprehensive Context System

| Phase | Description | Tasks | Effort |
|-------|-------------|-------|--------|
| A | Memory retrieval enhancement | 7 | 2-3 hours |
| B | Humanization pipeline wiring | 8 | 3-4 hours |
| C | Token budget expansion | 7 | 2-3 hours |
| D | Voice-text parity | 6 | 2-3 hours |
| **Total** | | **31** | **8-12 hours** |

### SDD Artifacts Created
- `specs/029-context-comprehensive/spec.md` ✅
- `specs/029-context-comprehensive/plan.md` ✅
- `specs/029-context-comprehensive/tasks.md` ✅
- `specs/029-context-comprehensive/audit-report.md` ✅ (PASS)

---

## Success Metrics (Post-Implementation)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Graph coverage | 33% | 100% | Code audit |
| Humanization active | 12.5% | 100% | Production logs |
| Token budget | 4,000 | 10,000+ | Prompt logs |
| Voice-text parity | 15% | 100% | Field comparison |
| User facts loaded | 5 | 50+ | Context snapshot |

---

## Next Steps

1. **Run `/implement specs/029-context-comprehensive/plan.md`**
2. Phase A first (memory retrieval) - highest impact
3. Phase B second (humanization wiring) - most tests
4. Phases C & D in parallel (token + voice)
5. E2E verification after all phases

---

## References

- **Audit session**: `workbook.md` (2026-01-15)
- **Research**: `docs-to-process/20260115-research-ai-companion-memory-systems-comprehensive-a8f3.md`
- **Spec**: `specs/029-context-comprehensive/`
- **Memory architecture**: `memory/architecture.md`
