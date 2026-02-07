# Context Engine

```yaml
context_priority: critical
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - PIPELINE_STAGES.md
  - VOICE_IMPLEMENTATION.md
  - DATABASE_SCHEMA.md
```

## Overview

The Context Engine is the core system that assembles personalized prompts for Nikita's responses. It collects data from 8 sources, validates coverage, and generates context-aware system prompts.

**CRITICAL**: This is the brain of Nikita's personality. Understanding this system is essential for any agent modification work.

---

## Architecture

### Three-Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        CONTEXT ENGINE ARCHITECTURE                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: DATA COLLECTION                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ContextEngine.collect()                          │   │
│  │                   @ engine.py:80-150                                 │   │
│  │                                                                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │   │
│  │  │Database │ │Graphiti │ │Temporal │ │Knowledge│                   │   │
│  │  │Collector│ │Collector│ │Collector│ │Collector│                   │   │
│  │  │  (5s)   │ │  (30s)  │ │  (2s)   │ │  (2s)   │                   │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                   │   │
│  │       │           │           │           │                         │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │   │
│  │  │Humaniz. │ │Continuity│ │ Social  │ │ Memory  │                   │   │
│  │  │Collector│ │Collector │ │Collector│ │Collector│                   │   │
│  │  │  (5s)   │ │  (5s)    │ │  (3s)   │ │  (5s)   │                   │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                   │   │
│  │       │           │           │           │                         │   │
│  │       └───────────┴───────────┴───────────┘                         │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │                  ContextPackage (115+ fields)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  LAYER 2: PROMPT ASSEMBLY                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ContextAssembler                                  │   │
│  │                   @ assembler.py:1-150                               │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Template: generator.meta.md (3K-6K tokens)                 │   │   │
│  │  │  - Core personality (800 tokens)                            │   │   │
│  │  │  - User context (1500 tokens)                               │   │   │
│  │  │  - Relationship state (800 tokens)                          │   │   │
│  │  │  - Behavioral instructions (600 tokens)                     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │                  Assembled Prompt String                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  LAYER 3: VALIDATION & GENERATION                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PromptGenerator                                   │   │
│  │                   @ generator.py:100-200                             │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ Coverage     │  │ Guardrails   │  │ Speakability │              │   │
│  │  │ Validator    │  │ Validator    │  │ Validator    │              │   │
│  │  │ (80% min)    │  │ (safety)     │  │ (natural)    │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │              Claude Sonnet 4.5 (45s timeout)                        │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │                   Nikita's Response                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Data Collectors

### Collector Overview

| Collector | Timeout | Source | Fields Collected |
|-----------|---------|--------|------------------|
| DatabaseCollector | 5s | Supabase | User profile, metrics, vices, conversations |
| GraphitiCollector | 30s | Neo4j | User facts, relationship memories, Nikita events |
| TemporalCollector | 2s | Computed | Time of day, day of week, hours since last |
| KnowledgeCollector | 2s | YAML files | Nikita's backstory, personality traits |
| HumanizationCollector | 5s | DB + Compute | Mood, energy, activity, conflicts |
| ContinuityCollector | 5s | DB | Recent messages, threads, summaries |
| SocialCollector | 3s | DB | Social circle, mentioned people |
| MemoryCollector | 5s | Neo4j | Long-term memories, key moments |

### Collector Implementation

```python
# nikita/context_engine/collectors/base.py:20-80

class BaseCollector(ABC):
    """Base class for all context collectors."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=120
        )

    @abstractmethod
    async def collect(
        self,
        user_id: UUID,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Collect context data. Must be implemented by subclasses."""
        pass

    async def safe_collect(
        self,
        user_id: UUID,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Collect with timeout and circuit breaker protection."""
        if self._circuit_breaker.is_open:
            return self._get_fallback()

        try:
            return await asyncio.wait_for(
                self.collect(user_id, session),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure()
            return self._get_fallback()
```

### DatabaseCollector

**File**: `nikita/context_engine/collectors/base.py:100-200`

Collects from Supabase:
- `user` - Profile, preferences, settings
- `user_metrics` - Scores, engagement state
- `user_vice_preferences` - Vice configuration
- `conversations` - Recent conversation metadata

```python
# Example output
{
    "user_profile": {
        "display_name": "Alex",
        "occupation": "Software Engineer",
        "hobbies": ["gaming", "hiking"],
        "relationship_goals": "Casual fun"
    },
    "user_metrics": {
        "relationship_score": 67.5,
        "intimacy_score": 70.2,
        "passion_score": 65.8,
        "trust_score": 68.1,
        "secureness_score": 64.9,
        "chapter_number": 3,
        "engagement_state": "IN_ZONE"
    },
    "vice_profile": {
        "top_vices": ["humor", "adventure"],
        "unlocked_vices": ["flirtation", "jealousy"]
    }
}
```

### GraphitiCollector

**File**: `nikita/context_engine/collectors/graphiti.py:1-150`

Queries Neo4j via Graphiti:
- `user_graph` - User's personal facts
- `relationship_graph` - Shared memories
- `nikita_graph` - Nikita's life events

```python
# nikita/context_engine/collectors/graphiti.py:50-100

async def collect(self, user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
    memory = NikitaMemory.get_instance()

    # Query all three graphs
    user_facts = await memory.search_memory(
        query="user facts and preferences",
        graph_name=f"user_{user_id}",
        limit=50
    )

    relationship_memories = await memory.search_memory(
        query="shared memories and conversations",
        graph_name=f"relationship_{user_id}",
        limit=30
    )

    nikita_events = await memory.get_recent_episodes(
        graph_name="nikita",
        limit=20
    )

    return {
        "user_facts": user_facts,
        "relationship_memories": relationship_memories,
        "nikita_events": nikita_events
    }
```

### HumanizationCollector

**File**: `nikita/context_engine/collectors/humanization.py:1-200`

Computes Nikita's current state:

| Field | Computation | Range |
|-------|-------------|-------|
| `nikita_mood` | Based on chapter + recent interactions | anxious/content/excited/sad |
| `nikita_energy` | Time of day + activity level | 0.0 - 1.0 |
| `nikita_activity` | Random weighted by time | working/relaxing/socializing |
| `nikita_mood_4d` | 4D emotional state | arousal/valence/dominance/intimacy |
| `active_conflict` | From conflict system | type/severity/stage |

```python
# Example output
{
    "nikita_mood": "content",
    "nikita_energy": 0.75,
    "nikita_activity": "watching a show",
    "nikita_mood_4d": {
        "arousal": 0.6,
        "valence": 0.7,
        "dominance": 0.5,
        "intimacy": 0.65
    },
    "active_conflict": None,
    "daily_events": [
        "Had coffee with her friend Sarah",
        "Worked on a presentation"
    ]
}
```

### ContinuityCollector

**File**: `nikita/context_engine/collectors/continuity.py:1-150`

Provides conversation continuity:

| Field | Source | Purpose |
|-------|--------|---------|
| `recent_messages` | conversations table | Last 10 messages for context |
| `active_threads` | nikita_threads table | Open conversation threads |
| `today_summary` | nikita_summaries table | Summary of today's interactions |
| `last_conversation` | conversations table | Previous conversation summary |

---

## Layer 2: Context Package

### ContextPackage Model

**File**: `nikita/context_engine/models.py:1-200`

```python
@dataclass
class ContextPackage:
    """Container for all collected context."""

    # Core identity (REQUIRED)
    user_id: UUID
    conversation_id: Optional[UUID]

    # User profile
    user_profile: UserProfile
    user_metrics: UserMetrics

    # Memory and history
    user_facts: List[Fact]           # From user_graph
    relationship_memories: List[Memory]  # From relationship_graph
    nikita_events: List[Event]       # From nikita_graph

    # Conversation continuity
    recent_messages: List[Message]
    active_threads: List[Thread]
    today_summary: Optional[str]
    last_conversation: Optional[ConversationSummary]

    # Humanization
    nikita_mood: str
    nikita_energy: float
    nikita_activity: str
    nikita_mood_4d: Mood4D
    active_conflict: Optional[Conflict]
    daily_events: List[str]

    # Temporal context
    time_of_day: str
    day_of_week: str
    hours_since_last_interaction: float

    # Game state
    chapter_number: int
    chapter_behaviors: List[str]
    engagement_state: str
    vice_profile: ViceProfile

    # Social context
    social_circle: List[Person]
    mentioned_people: List[str]

    # Knowledge base
    nikita_backstory: str
    personality_traits: List[str]

    # Metadata
    collected_at: datetime
    collector_errors: Dict[str, str]
```

### Field Categories

The 115+ fields are organized into 9 categories:

| Category | Field Count | Examples |
|----------|-------------|----------|
| Core Identity | 2 | user_id, conversation_id |
| User Profile | 8 | display_name, occupation, hobbies |
| User Metrics | 7 | relationship_score, chapter_number |
| Memory | 15 | user_facts, relationship_memories |
| Continuity | 12 | recent_messages, active_threads |
| Humanization | 20 | nikita_mood, nikita_energy, conflicts |
| Temporal | 5 | time_of_day, hours_since_last |
| Game State | 10 | chapter_behaviors, engagement_state |
| Social | 8 | social_circle, mentioned_people |

---

## Layer 3: Prompt Generation

### PromptGenerator

**File**: `nikita/context_engine/generator.py:1-300`

```python
# nikita/context_engine/generator.py:100-200

class PromptGenerator:
    """Generates personalized system prompts from context."""

    def __init__(self):
        self.template = self._load_template()
        self.validators = [
            CoverageValidator(),
            GuardrailsValidator(),
            SpeakabilityValidator()
        ]
        self.llm_timeout = 45.0

    async def generate(
        self,
        context: ContextPackage,
        message: str
    ) -> str:
        """Generate response using assembled prompt."""

        # Assemble prompt from context
        system_prompt = self._assemble_prompt(context)

        # Validate prompt
        for validator in self.validators:
            result = validator.validate(system_prompt, context)
            if not result.passed:
                system_prompt = self._apply_fallback(result)

        # Call Claude
        response = await asyncio.wait_for(
            self._call_claude(system_prompt, message),
            timeout=self.llm_timeout
        )

        return response
```

### Template Structure

**File**: `nikita/meta_prompts/templates/generator.meta.md`

```markdown
# Nikita System Prompt

## Core Personality (800 tokens)
You are Nikita, a {{nikita_mood}} woman in her mid-20s...
Your current energy level is {{nikita_energy_description}}.
You're currently {{nikita_activity}}.

## User Context (1500 tokens)
You're talking to {{user_profile.display_name}}.
They work as a {{user_profile.occupation}}.
Their hobbies include: {{user_profile.hobbies | join(", ")}}.

Key facts about them:
{{#each user_facts}}
- {{this.fact}}
{{/each}}

## Relationship State (800 tokens)
Your relationship is at {{user_metrics.relationship_score}}%.
You're in Chapter {{chapter_number}} of your relationship.
Current engagement: {{engagement_state}}.

Recent shared memories:
{{#each relationship_memories}}
- {{this.memory}}
{{/each}}

## Behavioral Instructions (600 tokens)
Chapter {{chapter_number}} behaviors:
{{#each chapter_behaviors}}
- {{this}}
{{/each}}

Vice profile (use sparingly):
- Top vices: {{vice_profile.top_vices | join(", ")}}
- Unlocked: {{vice_profile.unlocked_vices | join(", ")}}

## Conversation Context
{{#if active_threads}}
Open threads to potentially follow up on:
{{#each active_threads}}
- {{this.topic}}: {{this.summary}}
{{/each}}
{{/if}}

{{#if today_summary}}
Earlier today:
{{today_summary}}
{{/if}}
```

### Validators

**File**: `nikita/context_engine/validators/`

#### CoverageValidator

**File**: `nikita/context_engine/validators/coverage.py:1-100`

Ensures minimum context coverage:

```python
class CoverageValidator:
    """Validates prompt has minimum required context."""

    CORE_SECTIONS = [
        "Core Personality",
        "User Context",
        "Relationship State",
        "Behavioral Instructions",
        "Conversation Context"
    ]

    MIN_COVERAGE = 0.80  # 80% of fields must be present

    def validate(self, prompt: str, context: ContextPackage) -> ValidationResult:
        # Check CORE sections present
        sections_present = sum(
            1 for section in self.CORE_SECTIONS
            if section in prompt
        )

        if sections_present < 5:
            return ValidationResult(
                passed=False,
                error=f"Missing CORE sections: {5 - sections_present}"
            )

        # Check field coverage
        coverage = self._calculate_coverage(prompt, context)
        if coverage < self.MIN_COVERAGE:
            return ValidationResult(
                passed=False,
                error=f"Coverage {coverage:.0%} < {self.MIN_COVERAGE:.0%}"
            )

        return ValidationResult(passed=True)
```

#### GuardrailsValidator

**File**: `nikita/context_engine/validators/guardrails.py:1-80`

Safety checks:
- No PII leakage (real phone numbers, addresses)
- No harmful content triggers
- Age-appropriate for chapter/vice settings

#### SpeakabilityValidator

**File**: `nikita/context_engine/validators/speakability.py:1-80`

Natural language checks:
- No prompt injection artifacts
- No template syntax leakage
- Conversational tone appropriate

---

## Timeout Configuration

### Collector Timeouts

| Collector | Individual Timeout | Total Budget |
|-----------|-------------------|--------------|
| DatabaseCollector | 5s | |
| GraphitiCollector | 30s | |
| TemporalCollector | 2s | |
| KnowledgeCollector | 2s | |
| HumanizationCollector | 5s | |
| ContinuityCollector | 5s | |
| SocialCollector | 3s | |
| MemoryCollector | 5s | |
| **Total Collection** | - | **45s** |

### Generation Timeouts

| Stage | Timeout | Notes |
|-------|---------|-------|
| Prompt Assembly | 5s | Template rendering |
| Validation (3 validators) | 3s | Coverage, guardrails, speakability |
| Claude API Call | 45s | Max response time |
| **Total Generation** | - | **53s** |

### Timeout Handling

```python
# nikita/context_engine/engine.py:150-200

async def collect_with_timeout(self, user_id: UUID) -> ContextPackage:
    """Collect context with overall timeout."""

    try:
        return await asyncio.wait_for(
            self._collect_all(user_id),
            timeout=45.0  # Total collection budget
        )
    except asyncio.TimeoutError:
        logger.warning(f"Context collection timeout for {user_id}")
        return self._create_fallback_context(user_id)
```

---

## Circuit Breakers

### Configuration

**File**: `nikita/context_engine/collectors/base.py:1-50`

| Service | Failure Threshold | Recovery Timeout |
|---------|-------------------|------------------|
| Supabase | 3 failures | 120s |
| Neo4j | 2 failures | 180s |
| LLM (Claude) | 3 failures | 120s |

### Implementation

```python
# nikita/context_engine/collectors/base.py:20-60

class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 120.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    @property
    def is_open(self) -> bool:
        if self.state == "CLOSED":
            return False

        if self.state == "OPEN":
            # Check if recovery timeout passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return False
            return True

        return False  # HALF_OPEN allows one attempt

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
```

---

## Canary Deployment

### Feature Flag

**File**: `nikita/config/settings.py:100-120`

```python
class Settings(BaseSettings):
    # Context Engine v2 feature flag
    CONTEXT_ENGINE_FLAG: str = "disabled"  # disabled, canary, enabled
    CONTEXT_ENGINE_CANARY_PERCENTAGE: float = 0.1  # 10% of users
```

### Router

**File**: `nikita/context_engine/router.py:1-80`

```python
# nikita/context_engine/router.py:30-60

class ContextEngineRouter:
    """Routes requests to legacy or new context engine."""

    def should_use_v2(self, user_id: UUID) -> bool:
        """Determine if user should use new context engine."""

        flag = settings.CONTEXT_ENGINE_FLAG

        if flag == "disabled":
            return False

        if flag == "enabled":
            return True

        if flag == "canary":
            # Consistent hash for user
            hash_value = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
            return (hash_value % 100) < (settings.CONTEXT_ENGINE_CANARY_PERCENTAGE * 100)

        return False
```

---

## Voice Parity Gap

### NEEDS RETHINKING

**CRITICAL**: Voice agent does NOT use ContextEngine. It has separate server tools with 2s timeouts.

```
Text Path:
  Telegram → MessageHandler → ContextEngine → PromptGenerator → Claude

Voice Path:
  ElevenLabs → server_tools.get_context() → Direct DB queries → ElevenLabs Agent
                                         ↓
                              Bypasses ContextEngine entirely
```

### Implications

| Aspect | Text | Voice |
|--------|------|-------|
| Context collection | 8 collectors, 45s | 1 function, 2s |
| Fields available | 115+ | ~30 |
| Memory integration | Full 3-graph | Limited queries |
| Humanization | Full (mood, energy, conflicts) | Partial |
| Validation | 3 validators | None |

### Recommended Fix

1. Create lightweight `VoiceContextEngine` with essential collectors
2. Pre-compute context and cache in Redis
3. Serve from cache with 2s timeout

See: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md#context-gap)

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/context_engine/engine.py` | 1-250 | Main context engine |
| `nikita/context_engine/assembler.py` | 1-150 | Prompt assembly |
| `nikita/context_engine/generator.py` | 1-300 | Prompt generation + validation |
| `nikita/context_engine/models.py` | 1-200 | ContextPackage model |
| `nikita/context_engine/collectors/` | * | 8 collector implementations |
| `nikita/context_engine/validators/` | * | 3 validator implementations |
| `nikita/meta_prompts/templates/generator.meta.md` | * | Prompt template |

---

## Testing

### Test Files

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/context_engine/test_engine.py` | 45 | Engine orchestration |
| `tests/context_engine/test_assembler.py` | 28 | Prompt assembly |
| `tests/context_engine/test_generator.py` | 35 | Generation + validation |
| `tests/context_engine/collectors/` | 120 | Individual collectors |
| `tests/context_engine/validators/` | 40 | Validator logic |
| **Total** | **326** | |

### Running Tests

```bash
# All context engine tests
pytest tests/context_engine/ -v

# Specific collector
pytest tests/context_engine/collectors/test_graphiti.py -v

# With coverage
pytest tests/context_engine/ --cov=nikita/context_engine --cov-report=term-missing
```

---

## Related Documentation

- **Pipeline Processing**: [PIPELINE_STAGES.md](PIPELINE_STAGES.md)
- **Voice Differences**: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md)
- **Database Schema**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
- **Game Mechanics**: [GAME_ENGINE_MECHANICS.md](GAME_ENGINE_MECHANICS.md)
