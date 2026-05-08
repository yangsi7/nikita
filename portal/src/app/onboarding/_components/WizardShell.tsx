"use client"

import { useCallback, useEffect, useId, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"

import { useAnswerAPI } from "@/app/onboarding/hooks/use-answer-api"
import type {
  AnswerResponse,
  ArchetypeCard,
  SlotKind,
} from "@/app/onboarding/types/answer"

import { AgentSubspace } from "./AgentSubspace"
import { ArchetypeFallback } from "./ArchetypeFallback"
import { BackLink } from "./BackLink"
import { BackstoryArchetypeCards } from "./BackstoryArchetypeCards"
import { DeterministicTrack } from "./DeterministicTrack"
import {
  HobbyChips,
  hobbyPicksValid,
  serializeHobbies,
} from "./HobbyChips"
import { IdentityPair } from "./IdentityPair"
import { NikitaThinkingDots } from "./NikitaThinkingDots"
import { PersonalizingBadge } from "./PersonalizingBadge"
import { ProgressRail } from "./ProgressRail"
import { WhyWeAsk } from "./WhyWeAsk"
import { deriveAgentView } from "./agent-view"
import { Chips } from "./controls/Chips"
import { CityInput } from "./controls/CityInput"
import {
  CombinedDualTextarea,
  combinedDualValid,
} from "./controls/CombinedDualTextarea"
import { Radio } from "./controls/Radio"
import {
  SATURDAY_MORNING_OPTIONS,
  Scenarios,
  VOICE_TONE_OPTIONS,
} from "./controls/Scenarios"
import { Slider } from "./controls/Slider"
import { Tel } from "./controls/Tel"
import { TextInput } from "./controls/TextInput"
import {
  COMPLETION_SCREEN_INDEX,
  PERSONALIZING_SCREEN_INDEX,
  WIZARD_SCREENS,
  screenIndexForSlotsFilled,
  slotsFilledFromProgressPct,
  type ScreenConfig,
} from "./screen-config"

/** Time to surface NikitaThinkingDots if pending exceeds this. */
const THINKING_DOTS_AFTER_MS = 2000

/**
 * UUID generator for `turn_id`. Primary path: `crypto.randomUUID()` (the
 * Web Crypto standard, available in all evergreen browsers + Node 19+).
 * Fallback path: `Math.random()`-based base36 string. The fallback only
 * fires in environments without crypto (e.g., very old test runners) and
 * is acceptable because `turn_id` is a server-side idempotency key, not
 * a security token; collisions in the fallback path would simply force
 * the BE to treat the request as a new turn rather than a replay. We
 * never sign anything with this UUID.
 */
function makeTurnId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

interface WizardState {
  /** Current screen index 0..14. */
  screenIndex: number
  /** Last server response — flat 6-branch discriminated union per
   *  Spec 217-3A AC-9.1bis. Drives reaction text + followup + cards. */
  lastResponse: AnswerResponse | null
  /** Progress percentage projected from the BE. Tracked separately from
   *  `lastResponse` because the new flat union only carries progress on
   *  the deterministic_advance / completion branches; reaction / followup
   *  / field_error / turn_failure branches keep the prior progress. */
  progressPct: number
  /** Hydrated progress on resume (mirror of progressPct at mount-time). */
  hydratedProgressPct: number
  /** Link code surfaced by the completion branch (Telegram bind QR). */
  hydratedLinkCode: string | null
  /** Mirror of /onboarding/state.is_complete on resume. */
  hydratedIsComplete: boolean
  /** Field-error map from the most recent field_error response. Cleared
   *  on the next non-error response. */
  fieldErrors: Record<string, string> | null
  /**
   * Server-issued turn_id of the most recently APPLIED response. Drives
   * the AnimatePresence key (AC C1.16) so failure/retry envelopes that
   * stay on the same `screenIndex` still re-trigger the screen
   * transition — gives cinematic feedback for `output.kind === "failure"`.
   */
  lastTurnId: string | null
  /**
   * Cache of turn_ids per slot (I2). When the user retries a slot after
   * a transient failure, we MUST resend the same `turn_id` so the BE's
   * idempotency layer dedupes — otherwise a "first POST succeeded then
   * the second timed out" sequence could double-process slot 1. Keys are
   * cleared after a slot's POST returns success.
   */
  turnIdsBySlot: Partial<Record<SlotKind, string>>
  /** Pending POST in flight. */
  pending: boolean
  /** True after >2s pending — render thinking dots in place of reaction. */
  showThinkingDots: boolean
  /** Resume hydration in progress. */
  hydrating: boolean
  /** Resume "welcome back" first-render flag. */
  resumed: boolean
  /** Inline error banner copy (4xx other than 401). */
  errorBanner: string | null
  /** First-render flag for the C1.19 midpoint nudge. */
  midpointShown: boolean
  /**
   * Most recently submitted slot/value pair. Used by the archetype
   * fallback (Spec 217-2 FR-4a) to re-fire the BE turn when
   * `archetype_cards` arrives null, forcing a fresh pipeline run with
   * a new `turn_id` (the cached one is cleared on success).
   */
  lastSubmit: { slot: SlotKind; value: string } | null
  /** Per-slot user input — keyed by SlotKind. */
  inputs: {
    display_name: string
    age: string
    occupation: string
    city: string
    darkness_level: number
    primary_hobbies_picks: string[]
    primary_hobbies_other: string
    saturday_morning: string | null
    geek_out_on: string
    together_we_could: string
    same_weird_if: string
    voice_tone_pref: string | null
    backstory_pick: string | null
    phone: string
  }
  conversationId: string | null
}

const initialInputs: WizardState["inputs"] = {
  display_name: "",
  age: "",
  occupation: "",
  city: "",
  darkness_level: 5,
  primary_hobbies_picks: [],
  primary_hobbies_other: "",
  saturday_morning: null,
  geek_out_on: "",
  together_we_could: "",
  same_weird_if: "",
  voice_tone_pref: null,
  backstory_pick: null,
  phone: "",
}

export function WizardShell() {
  const router = useRouter()
  const reduceMotion = useReducedMotion()
  const api = useAnswerAPI()
  const headlineRef = useRef<HTMLHeadingElement | null>(null)
  const dualHelperId = useId()
  const whyId = useId()

  const [state, setState] = useState<WizardState>({
    screenIndex: 0,
    lastResponse: null,
    progressPct: 0,
    hydratedProgressPct: 0,
    hydratedLinkCode: null,
    hydratedIsComplete: false,
    fieldErrors: null,
    lastTurnId: null,
    turnIdsBySlot: {},
    pending: false,
    showThinkingDots: false,
    hydrating: true,
    resumed: false,
    errorBanner: null,
    midpointShown: false,
    lastSubmit: null,
    inputs: initialInputs,
    conversationId: null,
  })

  // Resume hydration on mount (C1.15) — fetch /onboarding/state and
  // animate ProgressRail from 0 to resumed pct + render reaction with
  // last-turn reply (or a "welcome back" first-person line).
  useEffect(() => {
    let cancelled = false
    const hydrate = async () => {
      try {
        const s = await api.getState()
        if (cancelled) return
        const last = s.last_assistant_turn ?? null
        // GH #488 (Walk A1 M3): "welcome back. let's pick up." was
        // shown on fresh signup because the fallback fired whenever
        // there was no last_assistant_turn — which is also the case
        // for new users. Gate the resume-mode copy on progress_pct > 0
        // so cold-start renders the welcome screen's static copy
        // (per WIZARD_SCREENS welcome screen) instead.
        const replyFromLast =
          (last && typeof last === "object" && "content" in last
            ? String((last as { content?: unknown }).content ?? "")
            : "") ||
          (s.progress_pct > 0 ? "welcome back. let's pick up." : "")
        // 217-3B: hydrate response synthesizes a `reaction` envelope so the
        // agent subspace shows the resume/last-reply text. Progress + link
        // code are tracked in dedicated state fields (hydratedProgressPct +
        // hydratedLinkCode) since the new flat union does not carry them
        // outside the deterministic_advance / completion branches.
        const hydratedResponse: AnswerResponse | null = replyFromLast
          ? { kind: "reaction", reaction_text: replyFromLast }
          : null
        setState((prev) => ({
          ...prev,
          hydrating: false,
          resumed: s.progress_pct > 0,
          conversationId: s.conversation_id,
          lastResponse: hydratedResponse,
          progressPct: s.progress_pct,
          hydratedProgressPct: s.progress_pct,
          hydratedLinkCode: s.link_code ?? null,
          hydratedIsComplete: s.is_complete,
          // Walk A1 H2 (GH #485): map progress_pct → screenIndex on
          // rehydration so revisits at progress > 0 resume at the next
          // missing slot instead of bouncing back to the welcome screen.
          // Cold-start (progress_pct === 0) preserves the welcome opener.
          // Completed flows route to the terminal cleared screen.
          screenIndex:
            s.is_complete && s.progress_pct >= 100
              ? WIZARD_SCREENS.length - 1
              : s.progress_pct > 0
                ? screenIndexForSlotsFilled(
                    slotsFilledFromProgressPct(s.progress_pct)
                  )
                : prev.screenIndex,
        }))
      } catch {
        if (!cancelled) {
          setState((prev) => ({ ...prev, hydrating: false }))
        }
      }
    }
    hydrate()
    return () => {
      cancelled = true
    }
  }, [api])

  // Pending → show thinking dots after 2s.
  useEffect(() => {
    if (!state.pending) return
    const id = window.setTimeout(() => {
      setState((prev) =>
        prev.pending ? { ...prev, showThinkingDots: true } : prev
      )
    }, THINKING_DOTS_AFTER_MS)
    return () => window.clearTimeout(id)
  }, [state.pending])

  // Focus headline on screen change (AC C1.12 focus management).
  useEffect(() => {
    headlineRef.current?.focus()
  }, [state.screenIndex])

  const screen: ScreenConfig =
    WIZARD_SCREENS[Math.min(state.screenIndex, WIZARD_SCREENS.length - 1)]!

  const submitOne = useCallback(
    async (slot: SlotKind, value: string): Promise<AnswerResponse | null> => {
      // Idempotency cache (I2): reuse the slot's pending turn_id so a
      // retry after a transient failure dedupes against the BE's
      // idempotency layer rather than double-processing.
      const cachedTurnId = state.turnIdsBySlot[slot]
      const turnId = cachedTurnId ?? makeTurnId()
      if (!cachedTurnId) {
        setState((prev) => ({
          ...prev,
          turnIdsBySlot: { ...prev.turnIdsBySlot, [slot]: turnId },
        }))
      }
      try {
        const res = await api.submitAnswer({
          slot_kind: slot,
          value,
          turn_id: turnId,
          conversation_id: state.conversationId,
        })
        setState((prev) => {
          // 217-3B AC-13.2: discriminated-union dispatch on `res.kind`.
          // Drop the cached turn_id only on the non-error branches; retry
          // path depends on it surviving across failure attempts.
          const nextCache = { ...prev.turnIdsBySlot }
          const isErrorBranch =
            res.kind === "field_error" || res.kind === "turn_failure"
          if (!isErrorBranch) {
            delete nextCache[slot]
          }
          // Project progress per branch (Hard Rule #4 — monotonic):
          // reaction / followup / field_error / turn_failure leave
          // prior progress intact; deterministic_advance + completion
          // ratchet upward.
          const nextProgress =
            res.kind === "deterministic_advance" ||
            res.kind === "completion"
              ? Math.max(prev.progressPct, res.progress_pct)
              : prev.progressPct
          return {
            ...prev,
            lastResponse: res,
            lastTurnId: turnId,
            turnIdsBySlot: nextCache,
            progressPct: nextProgress,
            // field_error map is sticky on its own branch only; cleared on
            // any non-error response so re-renders don't repaint stale
            // inline errors.
            fieldErrors:
              res.kind === "field_error" ? res.errors : null,
            // 217-2 FR-4a: cache the (slot, value) so the archetype
            // fallback can re-fire the BE turn when `archetype_cards`
            // arrives null. We do NOT cache the turn_id — retry MUST
            // mint a fresh one to force a new BE pipeline run.
            lastSubmit: { slot, value },
            // The completion branch is the only branch that carries the
            // post-handoff conversation_id back; keep the prior id on
            // every other branch.
            conversationId:
              res.kind === "completion"
                ? res.conversation_id
                : prev.conversationId,
            hydratedLinkCode:
              res.kind === "completion"
                ? res.link_code
                : prev.hydratedLinkCode,
            errorBanner: null,
          }
        })
        return res
      } catch (err) {
        const status = (err as { status?: number } | null)?.status
        if (status && status !== 401) {
          setState((prev) => ({
            ...prev,
            errorBanner: "couldn't reach the server. try again.",
          }))
        }
        return null
      }
    },
    [api, state.conversationId, state.turnIdsBySlot]
  )

  // 217-3B FR-10a: IdentityPair compound submit. Wraps the typed payload
  // into a JSON-encoded `value` string per the wire contract; BE parses
  // by `slot_kind === "identity_pair"`. Mirrors `submitOne`'s pending /
  // turn_id discipline.
  const handleIdentityPairSubmit = useCallback(
    (payload: { name: string; age: string }) => {
      // Cache the typed values into inputs so partial-error rerenders
      // surface them via initialName / initialAge (AC-10b.3).
      setState((prev) => ({
        ...prev,
        inputs: {
          ...prev.inputs,
          display_name: payload.name,
          age: payload.age,
        },
        pending: true,
        showThinkingDots: false,
      }))
      void (async () => {
        const res = await submitOne(
          "identity_pair",
          JSON.stringify(payload),
        )
        if (!res) return
        if (res.kind === "deterministic_advance") {
          setState((prev) => ({
            ...prev,
            screenIndex: prev.screenIndex + 1,
            pending: false,
          }))
          return
        }
        // field_error / reaction / followup / turn_failure all stay on
        // the same screen — pending flag clears via setState above.
        setState((prev) => ({ ...prev, pending: false }))
      })()
    },
    [submitOne],
  )

  const handleSubmit = useCallback(async () => {
    setState((prev) => ({ ...prev, pending: true, showThinkingDots: false }))
    try {
      const inputs = state.inputs
      const slot = screen.slot
      if (!slot) {
        // Welcome / completion — advance.
        if (screen.index === 0) {
          setState((prev) => ({
            ...prev,
            screenIndex: prev.screenIndex + 1,
            pending: false,
          }))
          return
        }
        if (screen.index === COMPLETION_SCREEN_INDEX) {
          // Completion CTA → dashboard.
          router.push("/dashboard")
          return
        }
        if (screen.index === PERSONALIZING_SCREEN_INDEX) {
          // Personalizing card has no Continue affordance; the timeout
          // in the success branch advances. No-op if reached manually.
          return
        }
        return
      }

      // Per-slot value extraction.
      let value: string
      switch (slot) {
        case "display_name":
        case "occupation":
        case "geek_out_on":
          value = inputs[slot].trim()
          break
        case "age":
          value = inputs.age.trim()
          break
        case "city":
          value = inputs.city.trim()
          break
        case "phone":
          value = inputs.phone.trim()
          break
        case "darkness_level":
          value = String(inputs.darkness_level)
          break
        case "primary_hobbies":
          value = serializeHobbies(
            inputs.primary_hobbies_picks,
            inputs.primary_hobbies_other
          )
          break
        case "saturday_morning":
          value = inputs.saturday_morning ?? ""
          break
        case "voice_tone_pref":
          value = inputs.voice_tone_pref ?? ""
          break
        case "together_we_could":
          // Combined screen — submit BOTH slots back-to-back.
          {
            const r1 = await submitOne(
              "together_we_could",
              inputs.together_we_could.trim()
            )
            if (!r1) return
            const r2 = await submitOne(
              "same_weird_if",
              inputs.same_weird_if.trim()
            )
            if (!r2) return
          }
          setState((prev) => ({
            ...prev,
            screenIndex: prev.screenIndex + 1,
            pending: false,
          }))
          return
        case "backstory_pick":
          value = inputs.backstory_pick ?? ""
          break
        case "same_weird_if":
          // Only reached if a future config splits the combined screen.
          value = inputs.same_weird_if.trim()
          break
        case "identity_pair":
          // Handled out-of-band by handleIdentityPairSubmit (the
          // IdentityPair compound control owns its own submit button).
          // Reaching here indicates a misconfigured screen; bail out.
          setState((prev) => ({ ...prev, pending: false }))
          return
      }

      const res = await submitOne(slot, value)
      if (!res) return

      // 217-3B AC-13.2: only the `completion` branch advances to the
      // personalizing/handoff card. Reaction / followup / field_error /
      // turn_failure stay on the same screen (the AgentSubspace surfaces
      // the agent text; the deterministic chrome locks if needed).
      if (res.kind === "completion") {
        setState((prev) => ({
          ...prev,
          screenIndex: PERSONALIZING_SCREEN_INDEX,
          pending: false,
        }))
        // Brief transition card so the user perceives the handoff;
        // dashboard is reached on the same tick (router prefetch keeps
        // this fast). Personalizing screen renders the loader.
        window.setTimeout(() => router.push("/dashboard"), 1500)
        return
      }
      // Non-advancing branches keep the user on the current screen.
      if (
        res.kind === "reaction" ||
        res.kind === "followup" ||
        res.kind === "field_error" ||
        res.kind === "turn_failure"
      ) {
        setState((prev) => ({ ...prev, pending: false }))
        return
      }
      // deterministic_advance → next screen.
      setState((prev) => ({
        ...prev,
        screenIndex: prev.screenIndex + 1,
        pending: false,
      }))
    } finally {
      setState((prev) => ({ ...prev, pending: false, showThinkingDots: false }))
    }
  }, [screen, state.inputs, submitOne, router])

  const handleBack = useCallback(() => {
    setState((prev) => ({
      ...prev,
      screenIndex: Math.max(0, prev.screenIndex - 1),
    }))
  }, [])

  // 217-2 FR-4a: re-fire the last submit when the archetype fallback
  // surfaces. Mints a fresh turn_id (via `submitOne`'s fallthrough
  // path — `turnIdsBySlot[slot]` is empty after success) so the BE
  // runs the backstory pipeline anew rather than serving the cached
  // null-cards response.
  const retryLastSubmit = useCallback(() => {
    const last = state.lastSubmit
    if (!last) return
    void submitOne(last.slot, last.value)
  }, [state.lastSubmit, submitOne])

  // Per-slot validation gate for the Continue button.
  const canContinue = (): boolean => {
    const slot = screen.slot
    const inp = state.inputs
    if (!slot) return true
    switch (slot) {
      case "display_name":
      case "occupation":
      case "geek_out_on":
        return inp[slot].trim().length > 0
      case "age": {
        const n = parseInt(inp.age.trim(), 10)
        return Number.isFinite(n) && n >= 1 && n <= 120
      }
      case "city":
        return inp.city.trim().length > 0
      case "phone":
        return inp.phone.trim().length >= 7
      case "darkness_level":
        return inp.darkness_level >= 0 && inp.darkness_level <= 10
      case "primary_hobbies":
        return hobbyPicksValid(
          inp.primary_hobbies_picks,
          inp.primary_hobbies_other
        )
      case "saturday_morning":
        return inp.saturday_morning !== null
      case "voice_tone_pref":
        return inp.voice_tone_pref !== null
      case "together_we_could":
        return combinedDualValid(inp.together_we_could, inp.same_weird_if)
      case "backstory_pick":
        return inp.backstory_pick !== null
      case "same_weird_if":
        return inp.same_weird_if.trim().length >= 10
      case "identity_pair":
        // IdentityPair owns its own Continue button; handleSubmit's
        // gate is unused for this slot.
        return false
    }
  }

  // 217-3B AC-13.2: derive view from the flat 6-branch union.
  const agentView = deriveAgentView(state.lastResponse)
  const archetypeCards: ArchetypeCard[] | null = agentView.archetypeCards
  const progressPct = state.progressPct

  // Show midpoint nudge once on saturday_morning screen (C1.19). The
  // flip from "show" to "shown" lives in a useEffect (N4) so we never
  // schedule state mutations during render.
  const showMidpointNudge =
    screen.midpointNudge === true && !state.midpointShown && !state.resumed
  useEffect(() => {
    if (showMidpointNudge) {
      setState((prev) =>
        prev.midpointShown ? prev : { ...prev, midpointShown: true }
      )
    }
  }, [showMidpointNudge])

  return (
    <div
      className="relative min-h-screen flex items-center justify-center px-4 py-16 bg-void"
      data-reduce-motion={reduceMotion ? "true" : "false"}
    >
      {/* AuroraOrbs paused (hidden) under prefers-reduced-motion (C1.4). */}
      {!reduceMotion && <AuroraOrbs />}
      <ProgressRail progressPct={progressPct} />

      <AnimatePresence mode="wait">
        {/*
          AnimatePresence key is `lastTurnId` (server-issued UUID per
          turn, AC C1.16) when present, falling back to a screen-init
          synthetic key on the first paint and on welcome/completion
          screens that don't issue a turn. This makes failure-envelope
          re-renders trigger the cinematic transition (e.g.,
          `output.kind === "failure"` for an under-18 input) even when
          the wizard stays on the same `screenIndex`.
        */}
        <motion.div
          key={state.lastTurnId ?? `screen-${screen.index}-init`}
          initial={
            reduceMotion
              ? false
              : { opacity: 0, y: 16, filter: "blur(8px)" }
          }
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={
            reduceMotion
              ? { opacity: 0 }
              : { opacity: 0, y: -16, filter: "blur(8px)" }
          }
          transition={
            reduceMotion
              ? { duration: 0 }
              : { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const }
          }
          className="relative w-full max-w-xl"
        >
          {screen.index >= 2 && (
            <BackLink onClick={handleBack} />
          )}
          <PersonalizingBadge pending={state.pending} />

          {/*
            217-3B sibling-DOM layout (AC-11.1, 11.2, 11.3, 11.4).
            DeterministicTrack and AgentSubspace are direct siblings
            of the same flex-col main container — overlay rendering
            (the legacy NikitaReaction-on-top-of-control bug 4) is
            removed. The previous QuestionCard wrap is dropped; the
            DeterministicTrack provides the card chrome.
          */}
          <main
            data-testid="wizard-main"
            aria-label="onboarding wizard"
            className="flex flex-col gap-4"
          >
            <DeterministicTrack
              disabled={agentView.locksDeterministic}
            >
              {showMidpointNudge && (
                <p className="text-xs text-foreground/50 mb-2">
                  Halfway. Six down, six to go.
                </p>
              )}

              <h1
                ref={headlineRef}
                tabIndex={-1}
                className="text-2xl sm:text-3xl font-semibold focus:outline-none"
              >
                {screen.headline}
              </h1>

              {screen.whyWeAsk && (
                <WhyWeAsk id={whyId} text={screen.whyWeAsk} />
              )}

              <div className="mt-6">
                {renderControl({
                  screen,
                  state,
                  setState,
                  whyId,
                  dualHelperId,
                  archetypeCards,
                  onArchetypeRetry: retryLastSubmit,
                  onIdentityPairSubmit: handleIdentityPairSubmit,
                })}
              </div>

              {state.errorBanner && (
                <div
                  role="alert"
                  className="mt-4 px-4 py-2 rounded-md border border-primary/40 bg-primary/10 text-sm"
                >
                  {state.errorBanner}
                  <button
                    type="button"
                    onClick={() =>
                      setState((p) => ({ ...p, errorBanner: null }))
                    }
                    className="ml-2 underline"
                  >
                    try again
                  </button>
                </div>
              )}

              {screen.control !== "personalizing" &&
                screen.control !== "identity_pair" && (
                  <div className="mt-6 flex justify-end">
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={
                        !canContinue() ||
                        state.pending ||
                        state.hydrating ||
                        agentView.locksDeterministic
                      }
                      aria-describedby={
                        screen.control === "dual_textarea"
                          ? dualHelperId
                          : undefined
                      }
                      className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-base font-semibold text-primary-foreground glow-rose-pulse transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {state.pending
                        ? "…"
                        : screen.index === 0
                          ? "begin"
                          : screen.index === COMPLETION_SCREEN_INDEX
                            ? "open portal"
                            : "continue"}
                    </button>
                  </div>
                )}
            </DeterministicTrack>

            {/* AgentSubspace — sibling to DeterministicTrack (AC-11.3). */}
            {state.showThinkingDots ? (
              <section
                data-testid="agent-subspace"
                data-mode="thinking"
                aria-live="polite"
                className="rounded-2xl border border-white/5 bg-white/[0.03] px-6 py-4 backdrop-blur-sm"
              >
                <NikitaThinkingDots />
              </section>
            ) : (
              <AgentSubspace
                view={agentView}
                reduceMotion={reduceMotion ?? false}
                onRetry={retryLastSubmit}
                turnId={state.lastTurnId}
              />
            )}
          </main>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// renderControl — dispatch by ControlType
// ---------------------------------------------------------------------------

function renderControl({
  screen,
  state,
  setState,
  whyId,
  dualHelperId,
  archetypeCards,
  onArchetypeRetry,
  onIdentityPairSubmit,
}: {
  screen: ScreenConfig
  state: WizardState
  setState: React.Dispatch<React.SetStateAction<WizardState>>
  whyId: string
  dualHelperId: string
  archetypeCards: ArchetypeCard[] | null
  onArchetypeRetry: () => void
  onIdentityPairSubmit: (payload: { name: string; age: string }) => void
}) {
  const ctl = screen.control
  const set = (
    patch: Partial<WizardState["inputs"]> | ((p: WizardState["inputs"]) => Partial<WizardState["inputs"]>)
  ) =>
    setState((prev) => ({
      ...prev,
      inputs: {
        ...prev.inputs,
        ...(typeof patch === "function" ? patch(prev.inputs) : patch),
      },
    }))

  if (ctl === null) return null

  switch (ctl) {
    case "text":
      switch (screen.slot) {
        case "display_name":
          return (
            <TextInput
              value={state.inputs.display_name}
              onChange={(v) => set({ display_name: v })}
              ariaLabel="your name"
              describedBy={whyId}
              autoComplete="given-name"
              placeholder="your name"
            />
          )
        case "age":
          return (
            <TextInput
              value={state.inputs.age}
              onChange={(v) => set({ age: v })}
              ariaLabel="your age"
              describedBy={whyId}
              inputMode="numeric"
              placeholder="age"
            />
          )
        case "occupation":
          return (
            <TextInput
              value={state.inputs.occupation}
              onChange={(v) => set({ occupation: v })}
              ariaLabel="what you do"
              describedBy={whyId}
              placeholder="what you do"
            />
          )
        default:
          return null
      }
    case "city":
      return (
        <CityInput
          value={state.inputs.city}
          onChange={(v) => set({ city: v })}
          describedBy={whyId}
        />
      )
    case "tel":
      return (
        <Tel
          value={state.inputs.phone}
          onChange={(v) => set({ phone: v })}
          describedBy={whyId}
        />
      )
    case "slider":
      return (
        <Slider
          value={state.inputs.darkness_level}
          onChange={(v) => set({ darkness_level: v })}
          describedBy={whyId}
        />
      )
    case "hobbies":
      return (
        <HobbyChips
          picks={state.inputs.primary_hobbies_picks}
          other={state.inputs.primary_hobbies_other}
          onPicksChange={(next) => set({ primary_hobbies_picks: [...next] })}
          onOtherChange={(v) => set({ primary_hobbies_other: v })}
        />
      )
    case "scenarios":
      return (
        <Scenarios
          options={SATURDAY_MORNING_OPTIONS}
          value={state.inputs.saturday_morning}
          onChange={(v) => set({ saturday_morning: v })}
          ariaLabel="saturday morning"
        />
      )
    case "radio":
      return (
        <Radio
          options={VOICE_TONE_OPTIONS}
          value={state.inputs.voice_tone_pref}
          onChange={(v) => set({ voice_tone_pref: v })}
          ariaLabel="voice tone preference"
        />
      )
    case "chips":
      return (
        <Chips
          options={VOICE_TONE_OPTIONS}
          value={state.inputs.voice_tone_pref}
          onChange={(v) => set({ voice_tone_pref: v })}
          ariaLabel="voice tone preference"
        />
      )
    case "textarea":
      return (
        <textarea
          value={state.inputs.geek_out_on}
          onChange={(e) => set({ geek_out_on: e.target.value })}
          rows={4}
          aria-label="what you geek out on"
          aria-describedby={whyId}
          aria-required="true"
          placeholder="explain it like nobody's heard of it"
          className="w-full px-4 py-3 rounded-md bg-white/5 border border-white/10 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      )
    case "dual_textarea":
      return (
        <CombinedDualTextarea
          togetherValue={state.inputs.together_we_could}
          oddValue={state.inputs.same_weird_if}
          onTogetherChange={(v) => set({ together_we_could: v })}
          onOddChange={(v) => set({ same_weird_if: v })}
          helperId={dualHelperId}
        />
      )
    case "archetype":
      // 217-2 FR-4a: BE has not delivered cards (or the answer turn
      // came back with `archetype_cards: null`). Surface a fallback
      // Alert with retry CTA after the 4 s grace window so the
      // wizard never strands the user on the placeholder.
      if (!archetypeCards) {
        return <ArchetypeFallback onRetry={onArchetypeRetry} />
      }
      return (
        <BackstoryArchetypeCards
          cards={archetypeCards}
          selectedLabel={state.inputs.backstory_pick}
          onSelect={(label) => set({ backstory_pick: label })}
        />
      )
    case "identity_pair":
      // 217-3B FR-10a: compound name+age control. Submit handler is
      // wired by WizardShell so the (slot, value) cache + idempotency
      // turn_id flow stay co-located with submitOne.
      return (
        <IdentityPair
          initialName={state.inputs.display_name}
          initialAge={state.inputs.age}
          fieldErrors={state.fieldErrors}
          disabled={state.pending || state.hydrating}
          onSubmit={onIdentityPairSubmit}
          describedBy={whyId}
        />
      )
    case "personalizing":
      // I1: post-completion handoff card. Only the loader renders; no
      // Continue button. The success-branch timeout in handleSubmit
      // pushes /dashboard.
      return (
        <div
          role="status"
          aria-label="personalizing"
          className="flex items-center gap-3 text-foreground/70"
        >
          <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
          <span>tuning her to you. one moment.</span>
        </div>
      )
  }
}
