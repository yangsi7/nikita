# Clarification Example: E-Commerce Checkout Feature

**Purpose**: Complete walkthrough of clarification process for a specification with multiple ambiguities.

---

## Input Specification (with markers)

```markdown
# Feature Specification: E-Commerce Checkout

## Overview
Build a checkout flow for our e-commerce platform.

## Functional Requirements

- **FR-001**: System MUST process payments [NEEDS CLARIFICATION: payment methods not specified]
- **FR-002**: System MUST calculate shipping costs [NEEDS CLARIFICATION: shipping calculation logic unclear]
- **FR-003**: System MUST validate addresses
- **FR-004**: System MUST handle inventory [NEEDS CLARIFICATION: inventory reservation timing not specified]

## User Stories

**US-001**: As a customer, I want to complete checkout quickly
- **AC-001**: Checkout completes in <3 steps
- **AC-002**: Payment processing is fast [NEEDS CLARIFICATION: "fast" is vague]

**US-002**: As a customer, I want secure payment
- **AC-003**: Payment data is encrypted
- **AC-004**: PCI compliance maintained
```

**Problem**: 4 [NEEDS CLARIFICATION] markers (exceeds Article IV limit of 3), plus vague AC-002.

---

## Phase 1: Scan and Detect Ambiguities

### Ambiguity Coverage Scan

Using clarification-checklist.md categories:

| Category | Status | Notes |
|----------|--------|-------|
| Functional Scope | Partial | Payment methods unclear, inventory unclear |
| Domain Model | Partial | Order/Payment/Inventory relationships undefined |
| UX Flow | Clear | 3-step checkout specified |
| Non-Functional (Performance) | Partial | "Fast" payment vague (AC-002) |
| Integration | Missing | Payment gateway not specified |
| Edge Cases | Missing | Out-of-stock handling undefined |
| Constraints | Missing | Budget/timeline not mentioned |
| Terminology | Partial | "Inventory reservation" needs definition |

**Coverage Score**: ∑(c_i) = 5(Partial) × 5 + 3(Missing) × 0 = 25/80 = 31.25%

**Readiness**: FAIL (< 70%) → Requires clarification

---

## Phase 2: Prioritize Questions (Max 5)

### Priority Analysis (Article IV order: Scope > Security > UX > Technical)

1. **Payment methods** (Scope, Priority 1) - Affects what gets built
2. **Inventory reservation timing** (Scope, Priority 1) - Affects checkout flow
3. **Shipping calculation** (Technical, Priority 4) - Implementation detail
4. **Payment performance** (Non-Functional, Priority 3) - User experience
5. **Payment gateway integration** (Integration, Priority 2) - External dependency

**Selected**: Questions 1, 2, 5, 4 (Scope → Security/Integration → UX → Technical)
**Deferred**: Question 3 (shipping calculation) - lowest impact, can be clarified later

---

## Phase 3: Interactive Clarification (4 Questions)

### Question 1: Payment Methods (Priority: Scope)

**Context**: FR-001 mentions "process payments" but doesn't specify which payment methods to support. This determines data model, integrations, and user flow.

**Question**: Which payment methods should the checkout support?

**Options**:
A) Credit/debit cards only (simplest, covers 80% of users)
B) Cards + PayPal (adds popular alternative, minor complexity)
C) Cards + PayPal + Apple Pay + Google Pay (comprehensive, maximum friction reduction)

**Recommendation**: Option C provides best user experience and competitive feature set.

**Impact**:
- Data model: Payment method type field, tokenization strategy
- Integrations: Stripe/PayPal SDKs, Apple Pay/Google Pay APIs
- UX: Payment method selection UI
- Security: PCI scope (tokenization vs direct handling)

**Intelligence Evidence**:
- project-intel.mjs --search "payment" found: src/checkout/payment.tsx:45 (existing Stripe integration)
- Recommendation: Extend existing Stripe integration (supports all methods)

---

**Answer to Q1**: Option C (Cards + PayPal + Apple Pay + Google Pay)

**Rationale**: We want to minimize checkout abandonment, and offering multiple payment methods is proven to improve conversion. Our existing Stripe integration already supports all these methods.

**Additional Context**: Use Stripe Payment Element for unified UI across all methods.

---

### Question 2: Inventory Reservation Timing (Priority: Scope)

**Context**: FR-004 mentions "handle inventory" but doesn't specify when inventory gets reserved (cart add? checkout start? payment confirmation?). This affects user experience and overselling risk.

**Question**: When should inventory be reserved?

**Options**:
A) On cart add (prevents overselling, but may hold inventory unnecessarily)
B) On checkout initiation (balances availability and flexibility)
C) On payment confirmation (maximum flexibility, risk of overselling)

**Recommendation**: Option B (checkout initiation) with 15-minute reservation timeout.

**Impact**:
- Data model: Inventory reservation table with timestamps
- Business logic: Reservation creation, timeout, and release
- UX: "Item reserved for 15 minutes" messaging
- Edge cases: Reservation expiry handling, stock replenishment

**Intelligence Evidence**:
- project-intel.mjs --search "inventory" found: src/inventory/stock.ts:67 (real-time stock checking)
- Recommendation: Add reservation layer on top of existing stock system

---

**Answer to Q2**: Option B (checkout initiation with 15-minute timeout)

**Rationale**: Prevents overselling while not holding inventory for users just browsing. 15 minutes is standard e-commerce practice (Amazon, Shopify use similar windows).

**Additional Context**: Release reservation automatically if user abandons or completes checkout. Show countdown timer in UI.

---

### Question 3: Payment Gateway (Priority: Integration)

**Context**: Need to integrate with payment processor but specification doesn't mention which one or if we have existing contracts.

**Question**: Which payment gateway should we integrate with?

**Options**:
A) Stripe (market leader, excellent developer experience, 2.9% + 30¢)
B) PayPal (lower fees for high volume, existing merchant relationships)
C) Square (good for physical + online, but limited international)

**Recommendation**: Option A (Stripe) based on existing integration evidence.

**Impact**:
- Integration: Stripe SDK, webhook handling, API key management
- Security: PCI compliance via Stripe Elements (no card data touches our servers)
- Fees: 2.9% + 30¢ per transaction (negotiate volume discount later)
- Features: Payment Element supports all methods in Q1

**Intelligence Evidence**:
- project-intel.mjs found: src/checkout/payment.tsx:45 (Stripe integration exists)
- Recommendation: Extend existing integration rather than adding new gateway

---

**Answer to Q3**: Option A (Stripe)

**Rationale**: We already have Stripe integrated and it supports all payment methods from Q1. Adding another gateway adds complexity without benefit.

**Additional Context**: Use Stripe Payment Element for unified UI. Existing API keys and webhook infrastructure can be reused.

---

### Question 4: Payment Performance Target (Priority: Non-Functional)

**Context**: AC-002 says "payment processing is fast" but "fast" is vague. Need specific, measurable target.

**Question**: What is the maximum acceptable payment processing time?

**Options**:
A) <2 seconds (excellent UX, requires optimized flow)
B) <5 seconds (good UX, more achievable, industry standard)
C) <10 seconds (acceptable, but may feel slow)

**Recommendation**: Option B (<5 seconds from submit to confirmation screen).

**Impact**:
- Architecture: May need async processing with webhooks for complex cases
- Monitoring: Payment latency tracking, alerts for p95 > 5s
- UX: Loading states, optimistic updates
- Testing: Performance tests with payment gateway sandbox

**Intelligence Evidence**:
- Stripe average API latency: 500ms (from Stripe docs)
- Our current payment flow: src/checkout/payment.tsx:67 (synchronous, ~2s average)
- Recommendation: Keep synchronous flow for cards (< 2s), async for ACH/bank transfers

---

**Answer to Q4**: Option B (<5 seconds p95, <2 seconds for card payments)

**Rationale**: Industry standard for card payments is <2s, but some payment methods (bank transfers, 3D Secure) require longer processing. 5-second p95 covers all methods while maintaining good UX.

**Additional Context**: Show loading spinner with progress messages. For methods requiring redirects (PayPal, 3D Secure), set expectation with "Redirecting to..." message.

---

## Phase 4: Update Specification

### Updated Requirements

```markdown
## Functional Requirements

- **FR-001**: System MUST support credit/debit cards, PayPal, Apple Pay, and Google Pay via Stripe Payment Element
- **FR-002**: System MUST calculate shipping costs [DEFERRED - to be clarified in implementation planning]
- **FR-003**: System MUST validate addresses using Stripe Address Element
- **FR-004**: System MUST reserve inventory on checkout initiation with 15-minute timeout
  - Release reservation on checkout completion or abandonment
  - Display countdown timer to user
  - Handle reservation expiry gracefully

## Non-Functional Requirements

- **NFR-001**: Payment processing MUST complete in <5 seconds (p95) from submit to confirmation
  - Card payments target: <2 seconds
  - Redirect-based methods (PayPal, 3D Secure): <5 seconds
- **NFR-002**: System MUST maintain PCI compliance via Stripe tokenization (card data never touches our servers)

## Integration Requirements

- **INT-001**: System MUST integrate with Stripe Payment Element for unified payment UI
- **INT-002**: System MUST use Stripe Address Element for address validation
- **INT-003**: System MUST handle Stripe webhooks for async payment confirmations

## User Stories (Updated)

**US-001**: As a customer, I want to complete checkout quickly
- **AC-001**: Checkout completes in ≤3 steps
- **AC-002**: Payment processing completes in <5 seconds (p95) ✓ (was vague, now specific)
- **AC-003**: Multiple payment methods available (cards, PayPal, Apple Pay, Google Pay)

**US-002**: As a customer, I want secure payment
- **AC-004**: Payment data tokenized via Stripe (PCI compliant)
- **AC-005**: Card data never stored on our servers

**US-003**: As a customer, I want to know my item is reserved
- **AC-006**: Inventory reserved on checkout start
- **AC-007**: Countdown timer shows reservation expiry (15 minutes)
- **AC-008**: Clear messaging if reservation expires
```

### Clarification Status

| Category | Status | Notes |
|----------|--------|-------|
| Functional Scope | Clear | Payment methods, inventory timing specified |
| Domain Model | Clear | Payment/Order/Inventory relationships defined |
| UX Flow | Clear | 3-step checkout with timers |
| Non-Functional | Clear | <5s payment, <2s cards |
| Integration | Clear | Stripe Payment Element, webhooks |
| Edge Cases | Partial | Reservation expiry handled, out-of-stock deferred |
| Constraints | Missing | Budget/timeline not mentioned (not critical for spec) |
| Terminology | Clear | Inventory reservation = 15-min hold on checkout start |

**Coverage Score**: ∑(c_i) = 6(Clear) × 10 + 1(Partial) × 5 = 65/80 = 81.25%

**Readiness**: PASS (> 70%) → Ready for implementation planning

**Remaining Ambiguities**: 1 [NEEDS CLARIFICATION] marker (shipping calculation) - deferred to implementation planning as low-priority technical detail

---

## Outcome

**Before Clarification**:
- 4 [NEEDS CLARIFICATION] markers
- 1 vague AC
- 31.25% coverage (FAIL)

**After Clarification** (4 questions):
- 1 [NEEDS CLARIFICATION] marker (deferred, low-priority)
- All ACs specific and testable
- 81.25% coverage (PASS)
- Ready for create-implementation-plan skill

**Time Investment**: ~15-20 minutes of clarification dialogue saved hours of rework during implementation.

---

## Key Success Factors

1. **Prioritization**: Asked high-impact questions first (Scope > Integration > Non-Functional)
2. **Evidence**: Used project-intel.mjs to find existing Stripe integration
3. **Recommendations**: Provided options with trade-offs, not open-ended questions
4. **Incremental Updates**: Updated spec after each answer to maintain consistency
5. **Measurable Targets**: Replaced "fast" with "<5 seconds p95"
6. **Deferred Low-Priority**: Shipping calculation left for implementation planning (appropriate level)

**Result**: Specification ready for technical planning with clear scope and minimal ambiguity.
