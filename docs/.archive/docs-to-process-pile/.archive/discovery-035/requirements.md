# Requirements: Nikita Context Surfacing Investigation

## Investigation Scope

### Primary Goals
1. **Map Context Flow**: Understand exactly how Nikita's life, psychology, backstory flows to both agents
2. **Audit Spec 035**: Verify Deep Humanization implementation matches the plan
3. **Research Best Practices**: Check against 2024-2026 character building standards
4. **Identify Gaps**: Find missing pieces in context surfacing
5. **Verify Tests**: Ensure tests CLEARLY prove the system works

### Critical Questions
| Question | Priority | Status |
|----------|----------|--------|
| How is context surfaced to text agent? | CRITICAL | Unknown |
| How is context surfaced to voice agent? | CRITICAL | Unknown |
| Is RAG/memory retrieval actually working? | CRITICAL | Unknown |
| Do both agents receive same psychological depth? | HIGH | Unknown |
| Are there tests proving context flows correctly? | HIGH | Unknown |
| Does implementation match Spec 035 plan? | HIGH | Unknown |

### Investigation Targets

**Text Agent (Pydantic AI + Claude)**:
- How is system prompt built?
- Where does message_history come from?
- How are psychological states injected?
- How does memory/RAG integrate?

**Voice Agent (ElevenLabs Conversational AI 2.0)**:
- How are dynamic variables populated?
- How does server tools pattern work?
- How is context passed to voice agent?
- Is there parity with text agent?

### Success Criteria
- [ ] Context flow diagrams for both agents
- [ ] Gap analysis with severity levels
- [ ] Best practices comparison
- [ ] Test verification with evidence
- [ ] Implementation plan for fixes

### Constraints
- Must verify against latest library documentation
- Must use multiple expert perspectives
- Must keep main context clean (use subagents)
- Must provide CLEAR test evidence

## Known Gaps (Pre-Investigation)
| Gap | Severity | Notes |
|-----|----------|-------|
| How context reaches agents | VERY HIGH | Core question |
| Voice-text parity | HIGH | Need to verify |
| RAG integration status | HIGH | Need evidence |
| Test coverage | HIGH | Need verification |
