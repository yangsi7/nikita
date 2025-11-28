# Phase 0: Pre-Specification Quality Gate

**Purpose**: Quality assessment before specification creation to ensure user input has sufficient detail and clarity.

---

## Quality Scoring System

**5 Quality Dimensions (0-10 scale each)**:

### Dimension 1: Problem Clarity (0-10)

**What to Assess**:
- Is the problem statement clear?
- Are pain points articulated?
- Is the impact measurable or describable?

**Scoring**:
- **10**: Crystal clear problem with specific pain points and measurable impact
- **7-9**: Clear problem, some details may need refinement
- **4-6**: Vague problem statement, missing context or impact
- **1-3**: Barely comprehensible, no clear problem defined
- **0**: No problem statement

**Example (Score 9)**:
```
Problem: Users cannot track order status after purchase
Pain Point: Support receives 50+ daily calls asking "where is my order"
Impact: 20 hours/week support time, poor customer satisfaction
```

### Dimension 2: Value Proposition (0-10)

**What to Assess**:
- Is business/user value articulated?
- Are benefits quantified or clearly described?
- Are success metrics mentioned?

**Scoring**:
- **10**: Clear value with quantified benefits and success metrics
- **7-9**: Value evident, benefits described
- **4-6**: Vague value proposition
- **1-3**: Unclear why this matters
- **0**: No value proposition

**Example (Score 8)**:
```
Value: Reduce support burden by 80% (save 16 hours/week)
User Benefit: Real-time order visibility, peace of mind
Success Metric: Support calls about order status < 10/week
```

### Dimension 3: Requirements Completeness (0-10)

**What to Assess**:
- Are key capabilities mentioned?
- Are user scenarios described?
- Are constraints or boundaries discussed?

**Scoring**:
- **10**: Comprehensive requirements with scenarios and constraints
- **7-9**: Most capabilities mentioned, some scenarios described
- **4-6**: Missing key requirements or scenarios
- **1-3**: Minimal requirements, no scenarios
- **0**: No requirements mentioned

**Example (Score 7)**:
```
Capabilities:
- View order status (in-progress, shipped, delivered)
- Track shipment location
- Estimate delivery date
- Receive notifications on status changes

Constraints:
- Must work for both logged-in and guest users
```

### Dimension 4: Technology-Agnostic (0-10)

**What to Assess**:
- Is input free of technical implementation details?
- Does it focus on WHAT/WHY not HOW?
- Are technical choices avoided?

**Scoring**:
- **10**: Pure WHAT/WHY, zero technical details
- **7-9**: Mostly WHAT/WHY, minor technical mentions
- **4-6**: Mix of WHAT and HOW
- **1-3**: Mostly HOW (implementation focused)
- **0**: All HOW, no WHAT/WHY

**Good (Score 10)**:
```
Users need to see their order status in real-time
```

**Bad (Score 3)**:
```
Create a React dashboard with PostgreSQL database and REST API endpoints
```

### Dimension 5: User-Centric (0-10)

**What to Assess**:
- Are user needs central to the description?
- Are personas or user types mentioned?
- Is user value clear?

**Scoring**:
- **10**: User needs drive everything, personas clear, value obvious
- **7-9**: User-focused, needs clear
- **4-6**: Mix of user and system perspectives
- **1-3**: System-centric, minimal user focus
- **0**: No user perspective

**Example (Score 9)**:
```
For: Customers who purchased items
Need: Know where their order is without calling support
Value: Peace of mind, self-service convenience
```

---

## Overall Score Calculation

```
overall_score = (problem_clarity + value_proposition + requirements_completeness +
                 technology_agnostic + user_centric) / 5
```

**Thresholds**:
- **≥ 7.0**: **PROCEED** to Phase 1 (Intelligence-First Context Gathering)
- **5.0-6.9**: **CLARIFY** - Request specific improvements before proceeding
- **< 5.0**: **BLOCK** - User description too vague, cannot create specification

---

## Decision Logic

### IF overall_score ≥ 7.0: PROCEED

```
✓ Quality assessment passed (score: <overall_score>/10)

Strengths:
- [Dimension with score ≥ 8]
- [Dimension with score ≥ 8]

Proceeding to Phase 1: Intelligence-First Context Gathering
```

### IF 5.0 ≤ overall_score < 7.0: CLARIFY

```
⚠ Quality assessment requires improvement (score: <overall_score>/10)

Deficiencies:
- [Dimension with score < 7]: <specific feedback>
- [Dimension with score < 7]: <specific feedback>

Please provide:
- [Specific missing information for low-scoring dimension]
- [Specific clarification needed]

Example questions:
- "What specific problem does this solve for users?"
- "How will success be measured?"
- "What are the must-have capabilities for MVP?"
```

**User must revise description and re-run skill.**

### IF overall_score < 5.0: BLOCK

```
❌ Quality assessment failed (score: <overall_score>/10)

Major Issues:
- [Dimension with score < 5]: <critical missing information>
- [Dimension with score < 5]: <critical missing information>

Cannot create specification without:
- Clear problem statement (what pain are we solving?)
- Defined user value (why does this matter?)
- Basic requirements (what capabilities are needed?)

Please provide a more detailed description including:
1. Problem: What issue are users facing?
2. Value: Why is solving this important?
3. Capabilities: What should the feature do?
4. Users: Who will benefit from this?
```

**User must provide substantial detail before re-running skill.**

---

## Enforcement Checklist

Before proceeding to Phase 1, verify:

- [ ] All 5 dimensions scored (0-10 scale)
- [ ] Overall score calculated (average of 5 dimensions)
- [ ] Decision based on threshold: PROCEED/CLARIFY/BLOCK
- [ ] If CLARIFY: Specific feedback provided with questions
- [ ] If BLOCK: Critical missing information identified
- [ ] If PROCEED: Strengths acknowledged, moving to Phase 1

---

## Common Quality Issues

**Problem Clarity Failures**:
- Vague: "Make the app better"
- Missing impact: "Users have trouble with X" (no consequences mentioned)
- Solution-focused: "Add a dashboard" (problem unclear)

**Value Proposition Failures**:
- No business value: "It would be cool to have"
- Unmeasurable: "Improve user experience" (how?)
- Tech-driven: "Use latest framework" (why?)

**Requirements Completeness Failures**:
- Single sentence: "Add search"
- No constraints: Missing boundaries or limits
- No scenarios: No "Given/When/Then" examples

**Technology-Agnostic Failures**:
- Implementation details: "Create React component with Redux state"
- Architecture mentioned: "Microservices with Kubernetes"
- Specific tools: "Use MongoDB and Express.js"

**User-Centric Failures**:
- System perspective: "The system needs to process data"
- No user mentioned: "Implement algorithm X"
- Tech benefits: "Use latest framework for maintainability"

---

**Next Phase**: If PROCEED, move to Intelligence-First Context Gathering
