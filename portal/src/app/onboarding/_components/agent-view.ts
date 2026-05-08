/**
 * deriveAgentView — pure helper distilling an `AnswerResponse` into the
 * sub-shape that the FE renders in the agent subspace + deterministic
 * track. Used by `WizardShell` and tested in isolation (Spec 217-3B
 * AC-T-B.3 / AC-13.2).
 *
 * The helper is the discriminated-union dispatch site for the 6 BE
 * `AnswerResponse.kind` branches. Each branch projects to:
 *   - `reactionText`        — agent reaction shown in AgentSubspace (typing
 *                             fades it; deterministic track stays enabled).
 *   - `followupQuestion`    — clarifying followup; deterministic chrome
 *                             locks until resolved.
 *   - `fieldErrors`         — per-sub-field error map for compound slots
 *                             (IdentityPair partial-validation).
 *   - `failureExplanation`  — terminal explanation when the agent's emission
 *                             retries are exhausted.
 *   - `archetypeCards`      — backstory archetype card list (only on the
 *                             deterministic_advance branch's backstory turn).
 *   - `progressPct`         — server-authoritative progress; `null` on
 *                             non-progress branches.
 *   - `isComplete`          — terminal-turn flag.
 *   - `linkCode`            — Telegram bind QR payload (completion only).
 *   - `nextSlotKind`        — next-prompt hint from BE.
 *
 * The helper does NOT mutate; it only narrows. Cumulative state lives in
 * the caller (per `.claude/rules/agentic-design-patterns.md` Hard Rule #1).
 */

import type {
  AnswerResponse,
  ArchetypeCard,
} from "@/app/onboarding/types/answer"

export interface AgentView {
  reactionText: string | null
  followupQuestion: string | null
  fieldErrors: Record<string, string> | null
  failureExplanation: string | null
  archetypeCards: ArchetypeCard[] | null
  progressPct: number | null
  isComplete: boolean
  linkCode: string | null
  nextSlotKind: string | null
  /** True when the deterministic input chrome must lock pending followup
   *  resolution (AC-12.1: reaction does NOT lock; followup DOES). */
  locksDeterministic: boolean
}

const EMPTY_VIEW: AgentView = {
  reactionText: null,
  followupQuestion: null,
  fieldErrors: null,
  failureExplanation: null,
  archetypeCards: null,
  progressPct: null,
  isComplete: false,
  linkCode: null,
  nextSlotKind: null,
  locksDeterministic: false,
}

export function deriveAgentView(response: AnswerResponse | null): AgentView {
  if (response === null) return EMPTY_VIEW
  switch (response.kind) {
    case "reaction":
      return {
        ...EMPTY_VIEW,
        reactionText: response.reaction_text,
      }
    case "followup":
      return {
        ...EMPTY_VIEW,
        followupQuestion: response.question_text,
        nextSlotKind: response.target_slot,
        locksDeterministic: true,
      }
    case "field_error":
      return {
        ...EMPTY_VIEW,
        fieldErrors: response.errors,
      }
    case "turn_failure":
      return {
        ...EMPTY_VIEW,
        failureExplanation: response.explanation,
      }
    case "deterministic_advance":
      // GH #568 fix: surface `reaction_text` so a ReactionOnly that
      // decorated a deterministic advance renders in agent-subspace
      // alongside the progress update.
      return {
        ...EMPTY_VIEW,
        archetypeCards: response.archetype_cards,
        progressPct: response.progress_pct,
        nextSlotKind: response.next_slot_kind,
        reactionText: response.reaction_text,
      }
    case "completion":
      // GH #568 fix: surface `reaction_text` on the terminal turn too.
      return {
        ...EMPTY_VIEW,
        progressPct: response.progress_pct,
        isComplete: true,
        linkCode: response.link_code,
        reactionText: response.reaction_text,
      }
    default: {
      // QA iter-1 NITPICK-2: exhaustiveness assertion. If a future BE
      // schema adds a new `kind` branch, this `never` assignment fails
      // type-check and surfaces drift at the failure site instead of
      // silently widening to `EMPTY_VIEW`.
      const _exhaustive: never = response
      throw new Error(
        `deriveAgentView: unhandled AnswerResponse kind: ${
          (_exhaustive as { kind?: string }).kind
        }`,
      )
    }
  }
}
