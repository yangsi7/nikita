# Plan — Subspec 217-3B FE Wizard Refactor

**Parent**: `subspecs/217-3B-fe-wizard-refactor/spec.md`
**Phase**: 5
**Date**: 2026-05-07

## Architecture

### Sibling DOM (FR-11)

`WizardShell.tsx` (post-refactor sketch):
```tsx
return (
  <main className="wizard-shell">
    <DeterministicTrack
      data-testid="deterministic-card"
      disabled={state.kind !== "deterministic"}
    >
      <QuestionCard slot={current} />
    </DeterministicTrack>

    <AgentSubspace data-testid="agent-subspace">
      <AnimatePresence mode="wait">
        {state.kind === "reaction" && (
          <ReactionBubble
            key="reaction"
            text={state.reaction_text}
            onDismiss={() => dispatch({ type: "dismiss_reaction" })}
          />
        )}
        {state.kind === "followup" && (
          <FollowupCard
            key="followup"
            payload={state.payload}
            onAnswer={(value) => postAnswer({ slot: state.payload.slot_to_fill, value })}
          />
        )}
      </AnimatePresence>
    </AgentSubspace>
  </main>
);
```

Both `<DeterministicTrack>` and `<AgentSubspace>` are sibling children of `<main>`. The vitest at AC-T-B.1 verifies `el.parentNode === other.parentNode`.

### Interaction locking (FR-12)

`<DeterministicTrack disabled={...}>` translates to `aria-disabled` + visual fade (Tailwind `pointer-events-none opacity-50`) when locked. Deterministic input REMAINS ENABLED during reaction state — typing dispatches `dismiss_reaction` AND advances normally (preserves user momentum per Phase-6 H-2 resolution).

### IdentityPair (FR-10b)

`screen-config.ts`:
```ts
{ kind: "identity_pair", control: "IdentityPair" }
```

`IdentityPair.tsx`:
```tsx
function IdentityPair({ onSubmit }: Props) {
  const [name, setName] = useState("");
  const [age, setAge] = useState<number | "">("");
  const [errors, setErrors] = useState<Record<string,string>>({});

  return (
    <Card>
      <Input value={name} onChange={...} aria-invalid={!!errors.name} />
      {errors.name && <p role="alert">{errors.name}</p>}
      <Input type="number" value={age} onChange={...} aria-invalid={!!errors.age} />
      {errors.age && <p role="alert">{errors.age}</p>}
      <Button onClick={() => onSubmit({name, age})} disabled={!name || age === ""}>continue</Button>
    </Card>
  );
}
```

On `field_error` from BE (per 217-3A AC-10a.2), parent reducer sets `errors`. Valid name preserved (state held in `<IdentityPair>` local — value not cleared on error response).

### Reducer (FR-13)

`useConversationState.ts:175 case "server_response"`:
```ts
case "server_response": {
  const r = action.payload;
  switch (r.kind) {
    case "deterministic_advance":
      return {
        ...state,
        kind: "deterministic",
        slots: mergeUnion(state.slots, r.output.extractions),  // cumulative; never overwrite
        progressPct: r.output.progress_pct,  // BE is SoT
        lastResponse: r,
      };
    case "reaction":
      return { ...state, kind: "reaction", reaction_text: r.reaction_text };
    case "followup":
      return { ...state, kind: "followup", payload: r.payload };
    case "field_error":
      return { ...state, errors: r.errors };  // preserves slot data
    default:
      return state;
  }
}
```

NO `setTimeout` anywhere in this reducer. Reaction dismissal is user-driven (typing OR "Got it" tap).

## Test Plan (TDD)

| Test file | Covers |
|---|---|
| `_components/__tests__/WizardShell.test.tsx` | Sibling DOM (parentNode equality), interaction locking, focusable count, AnimatePresence transitions |
| `hooks/__tests__/useConversationState.test.ts` | Discriminated-union dispatch (4 cases), no-setTimeout-on-reaction |
| `_components/__tests__/IdentityPair.test.tsx` | Full-valid POST, field_error rendering, valid-name preservation |

## LOC Estimate

| Section | LOC |
|---|---|
| WizardShell.tsx refactor (REMOVE old + ADD sibling DOM) | -50 +80 = +30 net |
| DeterministicTrack.tsx | 50 |
| AgentSubspace.tsx | 50 |
| IdentityPair.tsx | 80 |
| screen-config.ts extension | 10 |
| useConversationState.ts:175 | 30 |
| Type updates (5 files) | 30 |
| **Production total** | **~280** |
| Tests (3 files, ~40 each) | (~120, separate from PR cap per pr-workflow.md custom) |

## Risks

| Risk | Mitigation |
|---|---|
| AnimatePresence key collisions on rapid state transitions | Use unique keys per `state.kind` value |
| Interaction-locking race when followup arrives mid-deterministic-typing | Reducer preserves typed value (typing during followup state should still update local input but not POST) |
| Walk-protocol fixture step 9 doesn't recognize new data-testids | Update `portal/e2e/fixtures/index.ts` per Constraints in master spec.md |

## Dependencies

217-3A merged. BE emission contract MUST be stable before FE consumes.
