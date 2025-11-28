# Phase 2: Extract User Requirements (WHAT/WHY Only)

**Purpose**: Extract technology-agnostic requirements focusing on WHAT and WHY, not HOW.

**Article IV Compliance**: Specification MUST be technology-agnostic. No implementation details, tech stack, or architecture.

---

## Step 2.1: Problem Statement

**Extract from user input**:

```markdown
## Problem Statement

**What problem are we solving?**
[Clear description of the pain point or opportunity]

**Why does this matter?**
[Impact on users, business, or product]

**Who experiences this problem?**
[User types or personas affected]

**Current situation:**
[How users currently handle this, workarounds, pain points]
```

**Example**:
```markdown
## Problem Statement

**What problem are we solving?**
Customers cannot track order status after purchase, leading to anxiety and support calls.

**Why does this matter?**
Support receives 50+ daily calls asking "where is my order?", consuming 20 hours/week.
Customers have no visibility into shipping progress, causing dissatisfaction.

**Who experiences this problem?**
All customers who placed orders (both registered users and guests).

**Current situation:**
Customers must call support to ask about order status. Support manually checks shipping provider websites and relays information. Time-consuming for both parties.
```

---

## Step 2.2: User Stories with Priorities

**Format**:
```markdown
## User Story <N> - [Title] (Priority: P1/P2/P3)

**As a** [user type]
**I want to** [capability]
**So that** [value/benefit]

**Why P1/P2/P3**: [Rationale for priority]
**Independent Test**: [How to validate this story works standalone]

**Acceptance Scenarios**:
1. **Given** [state], **When** [action], **Then** [outcome]
2. **Given** [state], **When** [action], **Then** [outcome]
```

**Priority Levels**:
- **P1**: Must-have for MVP (core value, blocking for launch)
- **P2**: Important but not blocking (enhances core value)
- **P3**: Nice-to-have (deferred to future releases)

**Example**:
```markdown
## User Story 1 - View Order Status (Priority: P1)

**As a** customer who placed an order
**I want to** see my order status (processing, shipped, delivered)
**So that** I know when to expect my order without calling support

**Why P1**: Core functionality. Without this, feature has no value.
**Independent Test**: Create order, check status page shows "Processing" immediately

**Acceptance Scenarios**:
1. **Given** I placed an order, **When** I view order details, **Then** I see current status (processing/shipped/delivered)
2. **Given** order is shipped, **When** I view order details, **Then** I see tracking number and carrier
3. **Given** order is delivered, **When** I view order details, **Then** I see delivery timestamp

## User Story 2 - Real-Time Tracking (Priority: P2)

**As a** customer with a shipped order
**I want to** see real-time location updates
**So that** I can plan to be home for delivery

**Why P2**: Enhances core value but not required for MVP
**Independent Test**: Trigger shipment update, verify status page reflects new location within 5 minutes

**Acceptance Scenarios**:
1. **Given** order is in transit, **When** shipment location updates, **Then** order page shows new location
2. **Given** order is out for delivery, **When** I check status, **Then** I see estimated delivery time

## User Story 3 - Delivery Notifications (Priority: P3)

**As a** customer
**I want to** receive email/SMS when order status changes
**So that** I stay informed without actively checking

**Why P3**: Nice-to-have, can be added later
**Independent Test**: Trigger status change, verify notification sent within 10 minutes

**Acceptance Scenarios**:
1. **Given** order ships, **When** status changes to "Shipped", **Then** I receive notification
2. **Given** order delivered, **When** status changes to "Delivered", **Then** I receive notification
```

---

## Step 2.3: Functional Requirements

**WHAT (capabilities), not HOW (implementation)**:

```markdown
## Functional Requirements

**Core Capabilities**:
1. [Capability 1]: [Description]
2. [Capability 2]: [Description]
3. [Capability 3]: [Description]

**Data Visibility**:
- [What data users need to see]
- [What data users need to provide]

**User Interactions**:
- [Actions users can perform]
- [Feedback users receive]

**Constraints**:
- [Boundaries or limits]
- [Required integrations or dependencies]
- [Compliance or security requirements]
```

**Example**:
```markdown
## Functional Requirements

**Core Capabilities**:
1. **Status Visibility**: Display current order status with timestamp
2. **Tracking Integration**: Show tracking number and carrier for shipped orders
3. **History Timeline**: Show complete order lifecycle (placed → processing → shipped → delivered)

**Data Visibility**:
- Order number, date, total
- Current status with last updated timestamp
- Tracking number (if shipped)
- Estimated delivery date
- Shipment location updates (if available)

**User Interactions**:
- View order status from order confirmation email link
- View order status from account order history
- Refresh status to check for updates
- Copy tracking number to clipboard

**Constraints**:
- Must work for both registered users and guest checkouts
- Must integrate with existing shipping providers (FedEx, UPS, USPS)
- Order data must be accurate within 5 minutes of status change
- No personally identifiable information in guest-accessible URLs
```

---

## Step 2.4: Success Criteria

**Measurable outcomes (NOT technical metrics)**:

```markdown
## Success Criteria

**User-Centric Metrics**:
- [Metric 1]: [Target value]
- [Metric 2]: [Target value]

**Business Metrics**:
- [Metric 1]: [Target value]
- [Metric 2]: [Target value]

**Adoption Metrics**:
- [Metric 1]: [Target value]
```

**Example**:
```markdown
## Success Criteria

**User-Centric Metrics**:
- "Where is my order?" support calls < 10/week (currently 50/week)
- Customer satisfaction with order visibility: ≥ 4.5/5
- % of customers checking order status: ≥ 60%

**Business Metrics**:
- Support time on order inquiries: < 4 hours/week (currently 20 hours/week)
- Cost savings: ~$800/week in support time

**Adoption Metrics**:
- % of orders with status checks: ≥ 50%
- Average checks per order: 2-3
```

---

## Technology-Agnostic Checklist

**Before proceeding, verify NO technical details**:

- [ ] No framework mentions (React, Vue, Angular, etc.)
- [ ] No database choices (PostgreSQL, MongoDB, etc.)
- [ ] No architecture patterns (REST, GraphQL, microservices, etc.)
- [ ] No specific APIs or libraries
- [ ] No infrastructure details (AWS, Kubernetes, Docker, etc.)
- [ ] No technical metrics (latency, throughput, etc.)

**Good Examples** (WHAT/WHY):
- "Users need to see order status"
- "System must update status within 5 minutes"
- "Guest users can access their orders"

**Bad Examples** (HOW):
- "Create a React component that polls the API"
- "Store data in PostgreSQL with indexed queries"
- "Use WebSocket for real-time updates"

---

## Edge Cases

**Document boundary conditions and error scenarios**:

```markdown
## Edge Cases

**Boundary Conditions**:
- [Edge case 1]: [Expected behavior]
- [Edge case 2]: [Expected behavior]

**Error Scenarios**:
- [Error scenario 1]: [User-visible outcome]
- [Error scenario 2]: [User-visible outcome]

**Data Quality Issues**:
- [Issue 1]: [Handling approach]
```

**Example**:
```markdown
## Edge Cases

**Boundary Conditions**:
- Order placed but payment pending: Show "Processing - Awaiting Payment Confirmation"
- Order cancelled: Show cancellation reason and timestamp
- Order returned: Show return status and refund processing

**Error Scenarios**:
- Tracking number not yet available: Show "Label Created - Awaiting Pickup"
- Shipping provider API unavailable: Show last known status with retry option
- Guest order with lost/invalid token: Provide order lookup by email + order number

**Data Quality Issues**:
- Duplicate tracking numbers: Show most recent shipment only
- Missing expected delivery date: Estimate based on typical carrier timeframes
```

---

## Enforcement Checklist

Before proceeding to Phase 3, verify:

- [ ] Problem statement complete (what, why, who, current situation)
- [ ] User stories prioritized (P1/P2/P3 with rationale)
- [ ] User stories are independently testable
- [ ] Functional requirements are technology-agnostic
- [ ] Success criteria are measurable
- [ ] Edge cases documented
- [ ] NO technical implementation details

**Next Phase**: Proceed to Generate Specification (Phase 3)
