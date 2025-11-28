# Clarification Checklist

**Feature**: ###-feature-name
**Created**: YYYY-MM-DD
**Specification**: specs/###-feature-name/spec.md

---

## Purpose

Systematic ambiguity detection across 10+ categories to ensure specification completeness before planning.

**Constitutional Authority**: Article IV (Specification-First Development), Section 4.2

### CoD^Σ Scoring Model

**Coverage Notation**:
```
c ∈ {clear:10, partial:5, missing:0}  (coverage score per category)
∑(coverage) = ∑(c_i)  i=1..N          (total coverage score)
Coverage% = ∑(c_i) / (N × 10) × 100   (percentage complete)

Ready_for_planning ⇔ Coverage% ≥ 80 ∧ critical_gaps = 0
```

**Target**: Coverage% ≥ 80 (minimum 8 categories clear, 2 partial acceptable)

---

## Ambiguity Categories

### 1. Functional Scope & Behavior

**Questions**:
- What exactly does each action do?
- Which features are in scope vs out of scope?
- What are the boundaries of each capability?

**Coverage (CoD^Σ)**: c₁ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 2. Domain & Data Model

**Questions**:
- What entities exist in this domain?
- What are the relationships between entities?
- What is the cardinality (one-to-one, one-to-many, many-to-many)?

**Coverage (CoD^Σ)**: c₂ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 3. Interaction & UX Flow

**Questions**:
- How do users navigate between screens/steps?
- What is the exact sequence of actions?
- What triggers each transition?

**Coverage (CoD^Σ)**: c₃ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 4. Non-Functional Requirements

**Questions**:
- What are the performance targets? (latency, throughput)
- What is the expected scale? (users, data volume)
- What are the availability requirements?

**Coverage (CoD^Σ)**: c₄ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 5. Integration & Dependencies

**Questions**:
- Which external systems are involved?
- What data flows in and out?
- What are the integration points?

**Coverage (CoD^Σ)**: c₅ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 6. Edge Cases & Failure Scenarios

**Questions**:
- What happens when X fails?
- How are errors handled and communicated?
- What are the boundary conditions?

**Coverage (CoD^Σ)**: c₆ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 7. Constraints & Tradeoffs

**Questions**:
- What are the budget/resource limits?
- What are the technology constraints?
- What compliance requirements exist?

**Coverage (CoD^Σ)**: c₇ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 8. Terminology & Definitions

**Questions**:
- How are key terms defined?
- What does "active" mean in this context?
- How is "completion" determined?

**Coverage (CoD^Σ)**: c₈ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 9. Permissions & Access Control

**Questions**:
- Who can perform which actions?
- What are the authorization rules?
- How is access controlled?

**Coverage (CoD^Σ)**: c₉ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

### 10. State & Lifecycle

**Questions**:
- What states can entities be in?
- What triggers state transitions?
- Are there terminal states?

**Coverage (CoD^Σ)**: c₁₀ = [clear:10 | partial:5 | missing:0]

**Findings**:
- [Note specific ambiguities or "None - all clear"]

---

## Prioritization Matrix

**Impact Order** (Article IV, Section 4.2):
1. **Scope** (highest) - Affects what gets built
2. **Security** - Affects risk and compliance
3. **UX** - Affects user experience
4. **Technical** (lowest) - Implementation details

---

## Clarification Questions Generated

**Maximum**: 5 questions per iteration

**Current Count**: 0 / 5

### Question 1: [Category] (Priority: [Scope/Security/UX/Technical])

**Context**: [Why this matters]

**Question**: [Specific, focused inquiry]

**Options**:
A) [Option with tradeoffs]
B) [Option with tradeoffs]
C) [Option with tradeoffs]

**Recommendation**: [Option X] - [Rationale]

**Impact**: [What depends on this answer]

---

## Summary (CoD^Σ)

**Category Coverage**:
```
N = 10 (total categories)
∑(clear) = |{c_i : c_i = 10}| = 0
∑(partial) = |{c_i : c_i = 5}| = 0
∑(missing) = |{c_i : c_i = 0}| = 10

Total_score = ∑(c_i) i=1..10 = 0
Coverage% = Total_score / (N × 10) × 100 = 0/100 = 0%
```

**Readiness Gate** (CoD^Σ):
```
Ready ⇔ Coverage% ≥ 80 ∧ critical_gaps = 0
Current: Coverage% = 0% ⇒ ¬Ready (below threshold)
```

**Ready for Planning**: [ ] Yes | [x] No (requires ≥80% coverage)

**Remaining [NEEDS CLARIFICATION]**: 0 / 3 (max per spec.md, Article IV)

**Next Action**:
- [ ] Generate clarification questions (max 5)
- [ ] Update specification based on answers
- [ ] Re-run clarification scan
- [ ] Proceed to planning (when Coverage% ≥ 80)
