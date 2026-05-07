# Plan — Subspec 217-3A BE Emission Union

**Parent**: `subspecs/217-3A-be-emission-union/spec.md`
**Phase**: 5
**Date**: 2026-05-07

## Architecture

### Type definitions (FR-5)

`nikita/agents/onboarding/converse_contracts.py` (extension):
```python
from pydantic import BaseModel, Field
from typing import Literal

class ReactionOnly(BaseModel):
    reaction_text: str = Field(max_length=140)

class FollowUpQuestion(BaseModel):
    reaction_text: str | None = Field(default=None, max_length=140)
    question_text: str = Field(max_length=240)
    control_type: Literal["text", "chips", "slider", "scenarios", "radio", "tel"]
    control_options: list[str] | None = None
    slot_to_fill: str  # ad-hoc follow-up slot key

class TurnFailure(BaseModel):
    explanation: str
```

### Agent wiring (FR-5, FR-6)

`conversation_agent.py:266`:
```python
from pydantic_ai import Agent, ToolOutput, RunContext, ModelRetry

agent = Agent(
    model=...,
    deps_type=ConverseDeps,
    output_type=[
        ToolOutput(ReactionOnly, name="emit_reaction"),
        ToolOutput(FollowUpQuestion, name="ask_followup"),
        ToolOutput(TurnFailure, name="turn_failure"),
    ],
    instructions=build_instructions,  # callable
)

def build_instructions(ctx: RunContext[ConverseDeps]) -> str:
    state = ctx.deps.state
    return render(
        next_question=ctx.deps.next_question_text,
        missing=state.missing,
        decision_rule=DECISION_RULE_TEXT,
    )
```

### Output validator (FR-7)

`validators.py`:
```python
import difflib

@agent.output_validator
async def mirror_of_next_validator(ctx: RunContext[ConverseDeps], output) -> ...:
    if isinstance(output, FollowUpQuestion):
        next_q = ctx.deps.next_question_text
        ratio = difflib.SequenceMatcher(None, output.question_text.lower(), next_q.lower()).ratio()
        if ratio > 0.85:
            raise ModelRetry(f"Follow-up question mirrors next deterministic question (ratio={ratio:.2f}). Emit ReactionOnly or rephrase.")
    if isinstance(output, ReactionOnly):
        last_answer = ctx.deps.last_user_answer or ""
        if last_answer and last_answer.lower() in output.reaction_text.lower():
            raise ModelRetry("Reaction echoes user's answer verbatim. Use a different framing.")
    return output
```

### Sidecar state (FR-8)

`agent_emission_state.py`:
```python
from pydantic import BaseModel
from .converse_contracts import FollowUpQuestion

class AgentEmissionState(BaseModel):
    pending_followup: FollowUpQuestion | None = None
```

Persistence at `users.onboarding_profile.pending_followup` JSONB. Cleared by writing `null`.

### `/answer` dispatch (FR-9, FR-10a)

`portal_onboarding.py /answer`:
```python
result = await agent.run(user_input, message_history=msgs, deps=deps)

if isinstance(result.output, ReactionOnly):
    await user_repo.set_pending_followup(uid, None)
    return {"kind": "reaction", "reaction_text": result.output.reaction_text}

if isinstance(result.output, FollowUpQuestion):
    await user_repo.set_pending_followup(uid, result.output.model_dump())
    return {"kind": "followup", "payload": result.output.model_dump()}

if isinstance(result.output, TurnFailure):
    return {"kind": "turn_failure", "explanation": result.output.explanation}

# Else: deterministic answer path (no agent emission)
# - Apply slot update
# - If slot=="identity_pair": partial-validation per FR-10a
# - FinalForm gate
```

## Test Plan (TDD)

| Test file | Covers |
|---|---|
| `tests/agents/onboarding/test_emission_union.py` | AC-5.1, 5.2, 5.3, 6.1, 6.2 |
| `tests/agents/onboarding/test_output_validator_mirrors.py` | AC-7.1, 7.2, 7.3 |
| `tests/agents/onboarding/fixtures/similarity_calibration.py` | AC-7.4 |
| `tests/agents/onboarding/test_emission_state_sidecar.py` | AC-8.1, 8.2, 8.3, AC-T-1 |
| `tests/api/routes/test_emission_dispatch.py` | AC-9.1, 9.2, 9.3 |
| `tests/api/routes/test_identity_pair.py` | AC-10a.1, 10a.2, 10a.3 |
| `tests/agents/onboarding/test_agentic_flow_217.py` | AC-T-1..T-5 (cumulative monotonicity, completion-gate triplet, mock-LLM-wrong-tool recovery, agent.run contract, dynamic instructions) |

## LOC Estimate

| Section | LOC |
|---|---|
| Type defs (converse_contracts.py extension) | 30 |
| Agent wiring (conversation_agent.py) | 40 |
| Output validators (validators.py) | 50 |
| Sidecar (agent_emission_state.py) | 15 |
| Prompts update (prompts.py) | 30 |
| Route dispatch (portal_onboarding.py) | 80 |
| Tests (7 files, ~50 each avg) | 70 (counted toward 400 cap per pr-workflow.md? — typically NO; spec/test split) |
| **Production total** | **~245** |

Mid-implementation pre-flight: `git diff --stat origin/master...HEAD` after step 4. If production diff >350, split `@output_validator` + sidecar into 217-3A.1 PR (~80 LOC).

## Risks

| Risk | Mitigation |
|---|---|
| LOC overflow >350 | Pre-flight check + 217-3A.1 split contingency |
| `difflib` threshold mis-calibration | Calibration fixture (AC-7.4) BEFORE locking 0.85 |
| Pydantic AI `ToolOutput` syntax false-positive flag from reviewer | Phase-2 primary-source verification documents it; reference in PR body |
| 216-D / 216-E wiring break (archetypes / firecrawl) | Restate consumption contract in spec (§Pydantic AI Primitives Used); deps injection unconditional |

## Dependencies

217-2 merged.
