# Failure Modes: Common Clarification Issues

**Purpose**: Identify and fix the 10 most common clarification process failures.

---

## Failure 1: Too Many [NEEDS CLARIFICATION] Markers

**Symptom**: Specification has >3 [NEEDS CLARIFICATION] markers

**Impact**: Violates Article IV, Section 4.2 (max 3 markers)

**Solution**: Prioritize by impact, clarify highest-priority items first, defer low-priority technical details to implementation planning

**Validation**: Run clarification process until ≤3 markers remain

**Prevention**: Use clarification-checklist.md to identify critical ambiguities early, defer technical details

**Example**:
```markdown
❌ Before (5 markers):
- FR-001: Payment [NEEDS CLARIFICATION: methods]
- FR-002: Shipping [NEEDS CLARIFICATION: calculation]
- FR-003: Tax [NEEDS CLARIFICATION: rates]
- FR-004: Inventory [NEEDS CLARIFICATION: timing]
- AC-002: Fast [NEEDS CLARIFICATION: performance target]

✓ After (2 markers, 3 clarified):
- FR-001: Payment via cards, PayPal, Apple Pay, Google Pay
- FR-002: Shipping [NEEDS CLARIFICATION: calculation] (deferred to planning)
- FR-003: Tax rates from TaxJar API based on shipping address
- FR-004: Inventory reserved on checkout start (15-min timeout)
- AC-002: Payment completes in <5 seconds (p95)
```

---

## Failure 2: Open-Ended Questions

**Symptom**: Questions like "How should we handle payments?" without options or recommendations

**Impact**: Wastes time, invites scope creep, doesn't guide user to best practices

**Solution**: Always provide 2-3 options with trade-offs and a recommendation

**Validation**: Every question MUST have Options section with A/B/C choices

**Prevention**: Use question template from clarification-workflow.md

**Example**:
```markdown
❌ Bad:
"How should we handle inventory?"

✓ Good:
**Question: When should inventory be reserved?**

Options:
A) On cart add (prevents overselling, may hold unnecessarily)
B) On checkout initiation (balances availability and flexibility)
C) On payment confirmation (maximum flexibility, risk of overselling)

Recommendation: Option B with 15-minute timeout (industry standard)
```

---

## Failure 3: Asking More Than 5 Questions Per Iteration

**Symptom**: Presenting 6+ clarification questions at once

**Impact**: Violates Article IV requirement (max 5 questions per iteration), overwhelms user

**Solution**: Prioritize by impact (Scope > Security > UX > Technical), ask top 5 only, iterate if needed

**Validation**: Count questions before presenting, ensure ≤5

**Prevention**: Use priority order from clarification-workflow.md Phase 2

**Example**:
```markdown
❌ Before (8 questions):
1. Payment methods (Scope)
2. Shipping calculation (Technical)
3. Tax handling (Technical)
4. Inventory timing (Scope)
5. Address validation (Technical)
6. Email notifications (UX)
7. Performance targets (Non-Functional)
8. Error handling (Technical)

✓ After (5 questions, prioritized):
1. Payment methods (Scope - Priority 1)
2. Inventory timing (Scope - Priority 1)
3. Performance targets (Non-Functional - Priority 3)
4. Email notifications (UX - Priority 3)
5. Address validation (Technical - Priority 4)

Deferred to next iteration or implementation planning:
- Shipping calculation (Technical - low impact)
- Tax handling (Technical - API-dependent)
- Error handling (Technical - implementation detail)
```

---

## Failure 4: Not Updating Specification After Each Answer

**Symptom**: Collecting all answers then updating spec at the end

**Impact**: Introduces contradictions, misses dependencies between answers, wastes context

**Solution**: Update specification incrementally after EACH answer, verify no contradictions

**Validation**: Specification file timestamp changes after each answer

**Prevention**: Follow Phase 3 workflow (answer → update → next question)

**Example**:
```markdown
❌ Bad workflow:
Ask Q1 → Q2 → Q3 → Q4 → Q5 (collect all) → Update spec once (may have contradictions)

✓ Good workflow:
Ask Q1 → Answer Q1 → Update spec (verify) → Ask Q2 → Answer Q2 → Update spec (verify) → ...
```

---

## Failure 5: Accepting Ambiguous Answers

**Symptom**: User answers with "we'll figure it out later" or vague responses

**Impact**: Ambiguity remains, defeats purpose of clarification

**Solution**: Politely push back, explain impact of leaving ambiguous, offer more specific options

**Validation**: Every answer MUST result in specific, measurable requirement

**Prevention**: Emphasize impact in question context

**Example**:
```markdown
❌ Bad acceptance:
User: "Let's support the usual payment methods"
→ Accepted (still ambiguous)

✓ Good push-back:
User: "Let's support the usual payment methods"
→ "To ensure we build the right integrations, can you clarify which specific methods?
   Most e-commerce sites use:
   - Cards (Visa, Mastercard, Amex, Discover)
   - PayPal
   - Apple Pay / Google Pay
   Which of these should we prioritize?"
```

---

## Failure 6: No Prioritization (All Questions Same Priority)

**Symptom**: Asking technical details before scope questions

**Impact**: May clarify low-impact items while leaving critical ambiguities

**Solution**: Always prioritize using Article IV order: Scope > Security > UX > Technical

**Validation**: Question list sorted by priority before presentation

**Prevention**: Use clarification-checklist.md categories with priority weights

**Example**:
```markdown
❌ Wrong order (Technical first):
1. How should we calculate shipping? (Technical)
2. What payment methods? (Scope)
3. When to reserve inventory? (Scope)

✓ Correct order (Scope first):
1. What payment methods? (Scope - Priority 1)
2. When to reserve inventory? (Scope - Priority 1)
3. How should we calculate shipping? (Technical - Priority 4)
```

---

## Failure 7: Introducing Contradictions

**Symptom**: New requirement conflicts with existing requirement

**Impact**: Specification becomes inconsistent, implementation impossible

**Solution**: Check for contradictions after EACH update, resolve immediately

**Validation**: Run consistency check (grep for conflicting terms)

**Prevention**: Incremental updates with validation (Phase 4, Step 4.1)

**Example**:
```markdown
❌ Contradiction introduced:
Existing: "FR-001: System MUST complete checkout in 3 steps"
New: "FR-005: System MUST require address verification, payment method selection,
       shipping method selection, gift options, and promotional code entry"
→ Conflict: FR-005 requires >3 steps

✓ Resolved:
Updated FR-001: "System MUST complete checkout in ≤3 required steps
                 (address, payment, review). Optional steps (gift options, promo codes)
                 accessible via expandable sections within required steps."
```

---

## Failure 8: No Intelligence Evidence in Recommendations

**Symptom**: Recommendations without project-intel.mjs or MCP evidence

**Impact**: Recommendations may conflict with existing codebase patterns

**Solution**: ALWAYS query project-intel.mjs before making recommendations

**Validation**: Every recommendation MUST include "Intelligence Evidence" section

**Prevention**: Use clarification-workflow.md question template (includes evidence section)

**Example**:
```markdown
❌ No evidence:
Recommendation: Use Stripe for payments
(Why Stripe? What if project uses PayPal?)

✓ With evidence:
Recommendation: Use Stripe for payments

Intelligence Evidence:
- project-intel.mjs --search "payment" found:
  src/checkout/payment.tsx:45 (existing Stripe integration)
  src/config/stripe.ts:12 (API keys configured)
- Recommendation aligns with existing pattern, no new integration needed
```

---

## Failure 9: Iterating Forever (No Stopping Condition)

**Symptom**: Continuing clarification indefinitely, never marking specification ready

**Impact**: Analysis paralysis, delays implementation, diminishing returns

**Solution**: Use readiness gate - stop when coverage ≥70% and ≤3 markers remain

**Validation**: Calculate coverage score after each iteration, stop when threshold met

**Prevention**: Use clarification-checklist.md coverage formula

**Example**:
```markdown
Coverage := ∑(c_i) where c_i ∈ {clear: 10, partial: 5, missing: 0}
Readiness := Coverage / (10 × num_categories) ≥ 70%

Iteration 1: 45% coverage → Continue (below threshold)
Iteration 2: 68% coverage, 2 markers → Continue (close to threshold)
Iteration 3: 78% coverage, 1 marker → STOP ✓ (above threshold, ready)
```

---

## Failure 10: Not Tracking Coverage

**Symptom**: No way to measure if clarification is complete

**Impact**: Can't determine when to stop, may miss entire categories

**Solution**: Use clarification-checklist.md to track coverage across 10+ categories

**Validation**: Coverage matrix updated after each clarification

**Prevention**: Initialize coverage matrix in Phase 1, update in Phase 4

**Example**:
```markdown
## Clarification Coverage Matrix

| Category | Before | After Iteration 1 | After Iteration 2 |
|----------|--------|-------------------|-------------------|
| Functional Scope | Missing (0) | Partial (5) | Clear (10) |
| Domain Model | Partial (5) | Partial (5) | Clear (10) |
| UX Flow | Clear (10) | Clear (10) | Clear (10) |
| Non-Functional | Missing (0) | Missing (0) | Clear (10) |
| Integration | Missing (0) | Partial (5) | Clear (10) |
| Edge Cases | Missing (0) | Missing (0) | Partial (5) |
| Constraints | Missing (0) | Missing (0) | Missing (0) |
| Terminology | Partial (5) | Clear (10) | Clear (10) |
| Permissions | Missing (0) | Missing (0) | Missing (0) |
| State/Lifecycle | Missing (0) | Partial (5) | Clear (10) |

**Coverage**: 20/100 → 40/100 → 75/100 (READY ✓)
```

---

## Diagnostic Workflow

When clarification process fails:

1. **Check Article IV Compliance** (Failures 1, 3)
   - Max 3 [NEEDS CLARIFICATION] markers?
   - Max 5 questions per iteration?

2. **Check Question Quality** (Failures 2, 6)
   - Questions have options with recommendations?
   - Prioritized by impact (Scope > Security > UX > Technical)?

3. **Check Update Process** (Failures 4, 7)
   - Updating spec after EACH answer?
   - Checking for contradictions after each update?

4. **Check Answer Quality** (Failure 5)
   - Answers specific and measurable?
   - Pushing back on vague responses?

5. **Check Evidence** (Failure 8)
   - Recommendations include project-intel.mjs evidence?
   - Checking existing patterns before recommending?

6. **Check Stopping Conditions** (Failures 9, 10)
   - Tracking coverage with matrix?
   - Stopping at ≥70% coverage and ≤3 markers?

---

## Quick Fixes

**For each failure mode**:
1. Identify symptom (what looks wrong?)
2. Apply solution (specific fix from above)
3. Re-validate (check passes now?)
4. Document learning (update process notes)
