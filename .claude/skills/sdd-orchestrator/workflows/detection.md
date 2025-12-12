# SDD Intent Detection

## Purpose

Detect when user input indicates SDD workflow actions and categorize the intent.

---

## Intent Categories

### 1. Feature Creation (Phase 3)

**Trigger Patterns:**
```
feature_creation := [
  "create feature", "new feature", "build feature",
  "I want to create", "I want to build", "implement a",
  "/feature", "run /feature", "start a new feature",
  "add feature for", "develop a"
]
```

**Examples:**
- "I want to create a new authentication feature"
- "Let's build a user dashboard"
- "/feature 'real-time notifications'"

### 2. Implementation (Phase 8)

**Trigger Patterns:**
```
implementation := [
  "implement", "start coding", "develop", "code this",
  "/implement", "run /implement", "begin implementation",
  "write the code", "build it", "execute the plan"
]
```

**Examples:**
- "Implement the authentication spec"
- "/implement plan.md"
- "Start coding the API endpoints"

### 3. Audit (Phase 7)

**Trigger Patterns:**
```
audit := [
  "audit", "verify", "check", "validate",
  "/audit", "run audit", "quality check",
  "is everything ready", "can we implement"
]
```

**Examples:**
- "Audit the current spec"
- "/audit specs/005-auth/"
- "Verify the tasks are ready"

### 4. Planning (Phase 5)

**Trigger Patterns:**
```
planning := [
  "plan", "design", "architect", "structure",
  "/plan", "create plan", "implementation plan",
  "how should we build"
]
```

**Examples:**
- "Plan the authentication system"
- "/plan spec.md"
- "Design the architecture"

### 5. Status Check (Meta)

**Trigger Patterns:**
```
status := [
  "status", "progress", "where am I", "what's next",
  "SDD status", "workflow status", "current phase",
  "what should I do", "next step"
]
```

**Examples:**
- "What's the current SDD status?"
- "What should I do next?"
- "Where am I in the workflow?"

### 6. Foundation (Phases 1-2)

**Trigger Patterns:**
```
foundation := [
  "define product", "create product", "product definition",
  "/define-product", "run /define-product",
  "generate constitution", "create constitution",
  "/generate-constitution", "run /generate-constitution",
  "start from scratch", "new project setup"
]
```

**Examples:**
- "Let's define the product first"
- "/define-product"
- "Generate the constitution for this project"

---

## Detection Algorithm

```python
Intent_Patterns = {
    "feature_creation": [...],  # See Section 1
    "implementation": [...],    # See Section 2
    "audit": [...],             # See Section 3
    "planning": [...],          # See Section 4
    "status": [...],            # See Section 5
    "foundation": [...]         # See Section 6
}

def detect_sdd_intent(user_message):
    message_lower = user_message.lower()

    for category, patterns in Intent_Patterns.items():
        for pattern in patterns:
            if pattern in message_lower:
                return {
                    "detected": True,
                    "intent": category,
                    "trigger": pattern,
                    "confidence": "high" if pattern.startswith("/") else "medium"
                }

    return {"detected": False, "intent": None}
```

---

## Confidence Levels

| Trigger Type | Confidence | Action |
|--------------|------------|--------|
| Explicit command (`/feature`) | High (95%) | Proceed immediately |
| Strong keywords ("create feature") | Medium (80%) | Proceed with confirmation |
| Weak keywords ("build something") | Low (60%) | Ask for clarification |

---

## Non-SDD Patterns (Skip Orchestration)

Do NOT trigger SDD orchestration for:
- General questions about code
- Bug fixes without spec reference
- Documentation updates
- Git operations
- Configuration changes
- Research tasks

**Skip Patterns:**
```
non_sdd := [
  "fix bug", "debug", "help with", "explain",
  "what does", "how does", "git", "commit",
  "documentation", "readme", "config"
]
```

---

## Output Format

```json
{
  "detected": true,
  "intent": "feature_creation",
  "trigger": "create feature",
  "confidence": "medium",
  "suggested_action": "/feature"
}
```
