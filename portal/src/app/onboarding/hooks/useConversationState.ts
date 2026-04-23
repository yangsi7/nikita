/**
 * useConversationState — Spec 214 FR-11d reducer hook (T3.1, T3.3).
 *
 * Replaces `WizardStateMachine.ts` for the chat-first onboarding loop. Owns
 * the conversation turn array, server-owned progress percentage, extracted
 * fields, and confirmation/completion flags. Per tech-spec §5.2, the
 * reducer handles 10 distinct action types (hydrate, user_input,
 * server_response, server_error, timeout, retry, truncate_oldest, confirm,
 * reject_confirmation, clearPendingControl).
 *
 * StrictMode dedup: hydrate dispatch from useEffect is guarded by a 50ms
 * window (`STRICTMODE_GUARD_MS`). Without the guard, React 18+ StrictMode
 * double-mount would emit two hydrate actions and double-append turns.
 *
 * Turn-ceiling elision (NR1b.5): when `turns.length > TURN_CEILING` the
 * oldest entry is elided, but the extracted fields from that turn are
 * preserved in `elidedExtracted` so the reducer does not lose profile data.
 */

import { useCallback, useEffect, useReducer, useRef } from "react"

import type { ControlSelection, PromptType } from "../types/ControlSelection"
import type { ConverseResponse, Turn } from "../types/converse"

/** StrictMode hydrate-dedup window (ms). Double-mount in dev would otherwise
 *  fire hydrate twice inside a tick. 50ms is generous: typical StrictMode
 *  double-mount is synchronous; real user re-hydrations are >>50ms apart.
 *  Current: 50. History: — (initial value per tech-spec §5.2 / T3.1 AC). */
export const STRICTMODE_GUARD_MS = 50

/** Maximum conversation length before we start truncating oldest turns
 *  (per spec AC-NR1b.5). Keeps payloads within the backend 100-turn limit
 *  (`ConverseRequest.conversation_history: max_length=100`).
 *  Current: 100. History: — (initial value per tech-spec §5.2 / T3.1 AC). */
export const TURN_CEILING = 100

/** Client-side hard cap on the /converse round-trip. If the backend has not
 *  replied within this window we abort the fetch and emit an in-character
 *  fallback bubble via the `timeout` reducer action (AC-T3.10.2 @edge-case).
 *
 *  Current: 30000.
 *  History:
 *   - 30000 (GH #378, 2026-04-21): Walk P observed every wizard turn timing
 *     out at the prior 2500 ceiling. Backend split CONVERSE_TIMEOUT_MS into
 *     warm (8s) and cold (30s, for the 30s post-cold-start window). The
 *     client cannot distinguish cold vs warm, so it MUST adopt the larger
 *     value to cover Cloud Run scale-to-zero startups + LLM warmup.
 *   - 2500 (PR #363 QA iter-1 fix N1): wired the orphaned `timeout`
 *     reducer action. Rationale was tech-spec §11 SLO of 2.5 s "agent
 *     tail-latency"; that SLO turned out to be empirically wrong on prod.
 *
 *  Invariant: must be >= the backend cold timeout. Otherwise the client
 *  aborts a still-pending request and the user sees a fallback even though
 *  the backend would have completed. Enforced by a regression test in
 *  `__tests__/converse-timeout-invariant.test.ts`.
 */
export const CONVERSATION_AGENT_TIMEOUT_MS = 30000

export interface ConversationState {
  turns: Turn[]
  extractedFields: Record<string, unknown>
  /** Extracted fields from elided turns, preserved when truncation occurs. */
  elidedExtracted: Record<string, unknown>
  progressPct: number
  awaitingConfirmation: boolean
  currentPromptType: PromptType
  currentPromptOptions?: string[]
  isComplete: boolean
  isLoading: boolean
  lastError: string | null
  /** Pending link-telegram code minted by the reducer on conversation complete. */
  linkCode?: string
  linkCodeExpiresAt?: string
}

export type ConversationAction =
  | {
      type: "hydrate"
      turns: Turn[]
      extractedFields: Record<string, unknown>
      progressPct: number
      awaitingConfirmation: boolean
      currentPromptType?: PromptType
      currentPromptOptions?: string[]
      isComplete?: boolean
    }
  | { type: "user_input"; input: string | ControlSelection; turnId?: string }
  | { type: "server_response"; response: ConverseResponse }
  | { type: "server_error"; error: string }
  | { type: "timeout" }
  | { type: "retry" }
  | { type: "truncate_oldest" }
  | { type: "confirm" }
  | { type: "reject_confirmation" }
  | { type: "clearPendingControl" }
  | { type: "link_code"; code: string; expiresAt: string }

const INITIAL_STATE: ConversationState = {
  turns: [],
  extractedFields: {},
  elidedExtracted: {},
  progressPct: 0,
  awaitingConfirmation: false,
  currentPromptType: "text",
  isComplete: false,
  isLoading: false,
  lastError: null,
}

function renderUserContent(input: string | ControlSelection): string {
  if (typeof input === "string") return input
  return String(input.value)
}

export function conversationReducer(
  state: ConversationState,
  action: ConversationAction
): ConversationState {
  switch (action.type) {
    case "hydrate":
      // AC-T3.10.1 guard: when a Nikita turn already exists, do not let a late
      // hydrate overwrite active progress. Merge any missing hydrated turns
      // ahead of the active conversation instead.
      //
      // History:
      //   - Commit ebf06fb used `turns.length > 0` to block overwrites, but
      //     that was too broad: it also suppressed the opener when the user had
      //     only submitted a user_input turn (no nikita reply yet). Race:
      //     user fills + sends before getConversation() completes → turns=[user]
      //     → guard fired → opener never inserted → test saw 1 nikita bubble.
      //   - Correct invariant: hydrate must not overwrite active turns. A
      //     missing opener still needs to be prepended even after the reply won
      //     the race.
      if (state.turns.some((t) => t.role === "nikita")) {
        const missingHydratedTurns = action.turns.filter(
          (incoming) =>
            !state.turns.some(
              (existing) =>
                existing.role === incoming.role && existing.content === incoming.content
            )
        )
        if (missingHydratedTurns.length === 0) return state
        return { ...state, turns: [...missingHydratedTurns, ...state.turns] }
      }
      return {
        ...state,
        turns: action.turns,
        extractedFields: action.extractedFields,
        progressPct: action.progressPct,
        awaitingConfirmation: action.awaitingConfirmation,
        currentPromptType: action.currentPromptType ?? "text",
        currentPromptOptions: action.currentPromptOptions,
        isComplete: action.isComplete ?? false,
        isLoading: false,
        lastError: null,
      }

    case "user_input": {
      // GH #376: turn_id stays on the action envelope for idempotency header;
      // the Turn stored in state.turns must NOT carry it because state.turns
      // is spread into conversation_history on each converse call, and the
      // backend Turn model rejects extra fields (extra='forbid').
      const userTurn: Turn = {
        role: "user",
        content: renderUserContent(action.input),
        timestamp: new Date().toISOString(),
      }
      return {
        ...state,
        turns: [...state.turns, userTurn],
        isLoading: true,
        lastError: null,
      }
    }

    case "server_response": {
      const { response } = action
      const nikitaTurn: Turn = {
        role: "nikita",
        content: response.nikita_reply,
        timestamp: new Date().toISOString(),
        source: response.source,
      }
      // AC-T2.5.7 etc: extracted_fields are server-authoritative.
      const merged: Record<string, unknown> = {
        ...state.extractedFields,
        ...response.extracted_fields,
      }
      // AC-11d.7: if the terminal turn carries a link code, store it in state
      // so ClearanceGrantedCeremony can read the deep-link without a separate
      // POST /portal/link-telegram call. The code is minted server-side on the
      // same turn that sets conversation_complete=true (Spec 214 PR-B T12).
      const linkCodeUpdate =
        response.link_code != null
          ? { linkCode: response.link_code, linkCodeExpiresAt: response.link_expires_at ?? undefined }
          : {}
      return {
        ...state,
        turns: [...state.turns, nikitaTurn],
        extractedFields: merged,
        // AC-11d.5 monotonicity guard (GH #402/#403): progress can only
        // increase. Protects against transient BE regressions or stale
        // responses delivering a lower pct than the current state.
        progressPct: Math.max(state.progressPct, response.progress_pct),
        awaitingConfirmation: response.confirmation_required,
        currentPromptType: response.next_prompt_type,
        currentPromptOptions: response.next_prompt_options ?? undefined,
        isComplete: response.conversation_complete,
        isLoading: false,
        lastError: null,
        ...linkCodeUpdate,
      }
    }

    case "server_error":
      return {
        ...state,
        isLoading: false,
        lastError: action.error,
      }

    case "timeout": {
      // AC-T3.10.2 @edge-case: 2500ms timeout → in-character fallback bubble.
      const fallbackTurn: Turn = {
        role: "nikita",
        content: "i lost the signal for a sec. try again.",
        timestamp: new Date().toISOString(),
        source: "fallback",
      }
      return {
        ...state,
        turns: [...state.turns, fallbackTurn],
        isLoading: false,
        lastError: null,
      }
    }

    case "retry":
      return { ...state, isLoading: true, lastError: null }

    case "truncate_oldest": {
      if (state.turns.length === 0) return state
      const [oldest, ...rest] = state.turns
      const preserved: Record<string, unknown> = oldest.extracted
        ? { ...state.elidedExtracted, ...oldest.extracted }
        : state.elidedExtracted
      return {
        ...state,
        turns: rest,
        elidedExtracted: preserved,
      }
    }

    case "confirm":
      return { ...state, awaitingConfirmation: false, isLoading: true }

    case "reject_confirmation": {
      // AC-T3.7.2: mark latest Nikita turn as superseded.
      const turns = state.turns.slice()
      for (let i = turns.length - 1; i >= 0; i -= 1) {
        if (turns[i].role === "nikita") {
          turns[i] = { ...turns[i], superseded: true }
          break
        }
      }
      return {
        ...state,
        turns,
        awaitingConfirmation: false,
        // AC-T3.7.3 / M2: clear pending control until next server_response.
        currentPromptType: "none",
        currentPromptOptions: undefined,
      }
    }

    case "clearPendingControl":
      return {
        ...state,
        currentPromptType: "none",
        currentPromptOptions: undefined,
      }

    case "link_code":
      return { ...state, linkCode: action.code, linkCodeExpiresAt: action.expiresAt }

    default:
      return state
  }
}

export interface UseConversationStateResult {
  state: ConversationState
  dispatch: React.Dispatch<ConversationAction>
  hydrateOnce: (payload: {
    turns: Turn[]
    extractedFields: Record<string, unknown>
    progressPct: number
    awaitingConfirmation: boolean
    currentPromptType?: PromptType
    currentPromptOptions?: string[]
    isComplete?: boolean
  }) => void
}

/**
 * Hook API. `hydrateOnce` is the StrictMode-guarded entry point for loading
 * existing state on mount (from GET /portal/onboarding/profile or v2
 * localStorage). AC-T3.1.2: double-invocation within STRICTMODE_GUARD_MS is
 * a no-op; subsequent calls (e.g. genuine re-hydrates after timeout) work.
 */
export function useConversationState(): UseConversationStateResult {
  const [state, dispatch] = useReducer(conversationReducer, INITIAL_STATE)
  const lastHydrateMs = useRef<number>(0)

  const hydrateOnce = useCallback<UseConversationStateResult["hydrateOnce"]>(
    (payload) => {
      const now = Date.now()
      if (now - lastHydrateMs.current < STRICTMODE_GUARD_MS) return
      lastHydrateMs.current = now
      dispatch({ type: "hydrate", ...payload })
    },
    []
  )

  // Auto-truncate when the ceiling is crossed. Runs after each state update;
  // a single dispatch per overflow so we don't starve React's commit phase.
  useEffect(() => {
    if (state.turns.length > TURN_CEILING) {
      dispatch({ type: "truncate_oldest" })
    }
  }, [state.turns.length])

  return { state, dispatch, hydrateOnce }
}
