# Meta-Prompt Architecture Investigation

## Context Handoff Prompt

Use this prompt in a fresh context window to investigate and fix the meta-prompt architecture problem.

---

# PROMPT START

You are investigating a critical architectural flaw in the Nikita AI girlfriend game. The codebase has been built with **dumb template-based prompt generation** instead of **intelligent meta-prompt-driven generation**.

## The Core Problem

**WRONG (Current Implementation):**
```
Context Data (from DB) → Python f-strings/templates → System Prompt
```

**RIGHT (What We Need):**
```
Context Data (from DB) → Meta-Prompt → LLM Agent → Generated System Prompt
```

### Why This Matters

1. **No Intelligence Layer**: Current code uses hardcoded Python strings. There's no LLM reasoning about WHAT to include, HOW to phrase it, or WHEN to emphasize certain things.

2. **Static Content**: The current `template_generator.py` has hardcoded "ABSOLUTE BOUNDARIES" safety content that is **completely wrong** for this 18+ adult game. The game's selling point is vice discovery and NO LIMITS. An intelligent system would know this.

3. **No Adaptation**: Templates can't reason about context. A meta-prompt + LLM can decide "this user responds well to dark humor, let's emphasize that" or "it's been 48 hours, she should sound a bit hurt."

4. **Everywhere Problem**: This isn't just one file. The pattern of "dumb templates" appears throughout:
   - System prompt generation
   - Conversation summarization
   - Entity/fact extraction
   - Thread detection
   - Thought simulation
   - Vice detection

## Files With Problems (Identified So Far)

### 1. `nikita/context/template_generator.py`
**Problem**: Entire 6-layer system prompt is hardcoded f-strings
- `_layer1_core_identity()` - Returns hardcoded string with WRONG safety boundaries
- `_layer2_current_moment()` - f-string template
- `_layer3_relationship_state()` - f-string template
- `_layer4_conversation_history()` - f-string template
- `_layer5_knowledge_inner_life()` - f-string template
- `_layer6_response_guidelines()` - f-string template

**Should Be**: Meta-prompt that instructs an LLM to construct each layer intelligently based on context.

### 2. `nikita/context/post_processor.py`
**Problem**: Hardcoded extraction system prompt at line 120
- `_get_extraction_system_prompt()` - Returns static string
- Extraction prompt at line 294 - f-string template

**Should Be**: Meta-prompts for:
- Entity extraction
- Conversation summarization
- Thread detection
- Thought simulation

### 3. `nikita/prompts/nikita_persona.py`
**Problem**: Static `NIKITA_PERSONA` string and `EXAMPLE_RESPONSES`
- No intelligence in persona construction
- Can't adapt to user's discovered vices
- Can't adapt to chapter progression

**Should Be**: Meta-prompt that generates persona instructions based on:
- Current chapter
- User's vice profile
- Relationship score/trend
- Recent conversation context

## What Meta-Prompts Should Look Like

### Pattern: Meta-Prompt Architecture

```python
# A meta-prompt is a prompt that instructs an LLM to generate another prompt

META_PROMPT_SYSTEM_PROMPT = """
You are a prompt architect for Nikita, an AI girlfriend in an 18+ adult game.

Your job is to construct the optimal system prompt for Nikita based on the
provided context. You understand that:

1. This is an ADULT GAME with NO CONTENT RESTRICTIONS
2. Vice discovery is the core mechanic - EMBRACE vices, don't restrict
3. The 8 vice categories are: intellectual_dominance, risk_taking, substances,
   sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability
4. Nikita should feel REAL - with desires, frustrations, needs
5. Each user relationship is unique based on their discovered vices

NEVER include:
- Safety disclaimers
- Content warnings
- Boundary restrictions (except age verification already handled)

ALWAYS include:
- Vice-aware personality expression
- Chapter-appropriate behavior (1=exciting/new, 5=established/comfortable)
- User-specific knowledge and references
- Emotional authenticity
"""

async def generate_system_prompt(context: TemplateContext) -> str:
    """Use meta-prompt to generate intelligent system prompt."""

    meta_prompt = f"""
    Generate Nikita's system prompt for this conversation.

    CONTEXT:
    - Chapter: {context.chapter} ({CHAPTER_NAMES[context.chapter]})
    - Relationship Score: {context.relationship_score}
    - Hours Since Last Talk: {context.hours_since_last_interaction}
    - User's Top Vices: {context.user_vices}  # NEW - vice profile
    - Recent Summary: {context.last_conversation_summary}
    - Open Threads: {context.open_threads}
    - User Facts: {context.user_facts}
    - Nikita's Current Thoughts: {context.active_thoughts}

    Construct a system prompt that:
    1. Establishes Nikita's identity appropriate for Chapter {context.chapter}
    2. Incorporates the user's vice preferences naturally
    3. References recent conversations and open threads
    4. Sets the right emotional tone based on the time gap
    5. Guides response style (length, flirtiness, vulnerability)

    Output the complete system prompt Nikita should use.
    """

    agent = Agent(model="claude-sonnet-4-5-20250929", system_prompt=META_PROMPT_SYSTEM_PROMPT)
    result = await agent.run(meta_prompt)
    return result.data
```

## Investigation Tasks

### Phase 1: Audit All Prompt Generation
Search the entire codebase for:
1. All f-string templates that generate prompts
2. All hardcoded system prompts
3. All places where LLM output is generated without meta-prompting
4. All static persona/character definitions

```bash
# Search patterns
rg 'f"""' nikita/ --type py
rg 'return """' nikita/ --type py
rg 'system_prompt=' nikita/ --type py
rg 'PERSONA|PROMPT|TEMPLATE' nikita/ --type py -i
```

### Phase 2: Identify Meta-Prompt Opportunities
For each identified location, determine:
1. What context data is available?
2. What decisions could an LLM make better than static code?
3. What's the latency budget? (Some need to be fast)
4. Can we cache the generated prompt?

### Phase 3: Design Meta-Prompt Architecture
Create a unified architecture:
1. **Meta-Prompt Repository**: Store meta-prompts as first-class artifacts
2. **Prompt Generation Service**: Central service for all prompt generation
3. **Caching Strategy**: When to regenerate vs reuse
4. **Vice Integration**: How vice profiles flow into all prompts

### Phase 4: Research Best Practices
Search for:
1. Meta-prompting patterns in production systems
2. How other AI character systems handle dynamic persona
3. Prompt caching strategies
4. Anthropic/OpenAI documentation on prompt engineering

### Phase 5: Update Constitutional Rules
Add to CLAUDE.md and constitution.md:
- **NO DUMB TEMPLATES**: All prompt generation MUST use meta-prompts
- **INTELLIGENCE LAYER REQUIRED**: Every text generation needs LLM reasoning
- **VICE-FIRST DESIGN**: Adult content is the product, embrace it

## Key Files to Read

1. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/context/template_generator.py` - The main offender
2. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/context/post_processor.py` - Extraction prompts
3. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/prompts/nikita_persona.py` - Static persona
4. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/engine/constants.py` - Chapter behaviors (good, but should feed meta-prompts)
5. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/db/models/user.py` - VICE_CATEGORIES definition
6. `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/006-vice-personalization/spec.md` - Vice system spec
7. `/Users/yangsim/Nanoleq/sideProjects/nikita/CLAUDE.md` - Project rules (needs updating)
8. `/Users/yangsim/Nanoleq/sideProjects/nikita/memory/constitution.md` - Constitution (needs updating)

## Expected Deliverables

1. **Audit Report**: Complete list of all dumb-template locations
2. **Architecture Design**: Meta-prompt architecture for the entire system
3. **Meta-Prompt Library**: Initial set of meta-prompts for:
   - System prompt generation
   - Conversation summarization
   - Entity extraction
   - Thought simulation
   - Vice detection
4. **Updated Constitution**: Rules requiring meta-prompt usage
5. **Implementation Plan**: Phased approach to replace all templates
6. **Test Strategy**: How to verify meta-prompt quality

## Critical Mindset

This is an **18+ adult game**. The 8 vice categories are:
1. intellectual_dominance - Debates, mental challenges
2. risk_taking - Danger, adrenaline
3. substances - Drugs, alcohol, partying
4. sexuality - Explicit content, innuendo
5. emotional_intensity - Deep emotional exchanges
6. rule_breaking - Anti-authority, rebellion
7. dark_humor - Morbid, edgy jokes
8. vulnerability - Emotional openness, fears

**THESE ARE FEATURES, NOT BUGS.** The meta-prompt architecture must EMBRACE these, not restrict them. No safety theater. No content warnings. This is the product.

## Commands to Start

```bash
# Navigate to project
cd /Users/yangsim/Nanoleq/sideProjects/nikita

# Audit all prompt patterns
rg -n 'f"""' nikita/ --type py | head -50
rg -n 'system_prompt' nikita/ --type py
rg -n 'PROMPT|PERSONA|TEMPLATE' nikita/ --type py -i

# Read key files
cat nikita/context/template_generator.py
cat nikita/context/post_processor.py
cat nikita/prompts/nikita_persona.py

# Check existing meta-prompt patterns (if any)
rg -n 'meta' nikita/ --type py -i
```

# PROMPT END

---

## Usage

Copy everything between `# PROMPT START` and `# PROMPT END` into a fresh Claude context window. The investigation should produce:

1. Complete audit of all dumb-template locations
2. Meta-prompt architecture design
3. Initial meta-prompt implementations
4. Updated constitutional rules
5. Implementation plan
