"use client"

/**
 * PipelineGate — Step 10 of the wizard.
 *
 * Spec 214 FR-5 + FR-7. Posts the full profile on mount (once), polls
 * /pipeline-ready via `useOnboardingPipelineReady`, and renders the stamp
 * with a `data-state` attribute so Playwright can wait for the terminal
 * state without networkidle.
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5.
 * Renders the DossierReveal pipeline-stage panel driven by pipeline state
 * (teaching moment #3 from the design brief) — each completed stage adds
 * a ✓ line, then the CLEARED stamp lands on ready.
 *
 * State machine → stamp map:
 *   pending    → `clearance-pending` / PENDING (pulsing)
 *   ready      → `cleared` / CLEARED + auto-advance after 1.5s
 *   degraded   → `provisional` / PROVISIONAL — CLEARED + auto-advance
 *   timed out  → `provisional` / PROVISIONAL — CLEARED + advance
 *   failed     → `provisional` / PROVISIONAL — CLEARED (no hard block)
 *   submit 422 → show the Nikita-voiced "Something broke on our end."
 *   submit 409 → mount a testable rewind hint (orchestrator rewinds)
 */

import { useEffect, useRef, useState } from "react"
import * as FramerMotion from "framer-motion"

import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { DossierStamp } from "@/app/onboarding/components/DossierStamp"
import { DossierReveal } from "@/app/onboarding/components/DossierReveal"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import { useOnboardingAPI } from "@/app/onboarding/hooks/use-onboarding-api"
import { useOnboardingPipelineReady } from "@/app/onboarding/hooks/use-pipeline-ready"
import type { StepProps } from "@/app/onboarding/steps/types"
import type {
  OnboardingV2ProfileRequest,
  SocialScene,
  LifeStage,
} from "@/app/onboarding/types/contracts"

/**
 * How long to linger on the terminal stamp before auto-advancing to the
 * handoff step.
 *
 * Current: 1500ms (spec §FR-5 state-machine table)
 * Prior: — (initial Spec 214 value)
 * Rationale: matches the 1.5s stamp dwell in FR-5 so the user reads the
 *   cleared stamp before the handoff UI mounts.
 */
const AUTO_ADVANCE_DELAY_MS = 1500

/** Default cadence mirrors tuning.py PIPELINE_GATE_POLL_INTERVAL_S. */
const DEFAULT_POLL_INTERVAL_MS = 2000
/** Default hard cap mirrors tuning.py PIPELINE_GATE_MAX_WAIT_S. */
const DEFAULT_MAX_WAIT_MS = 20_000

/** Time after which the copy switches from "being processed" to "almost there". */
const LATE_COPY_THRESHOLD_MS = 15_000

type StampKind = "pending" | "ready" | "degraded" | "timeout"

/**
 * Pipeline-stage reveal items (teaching moment #3). Rows map to pipeline
 * progress signals from `useOnboardingPipelineReady` — as each signal
 * arrives, the corresponding ✓ row becomes visible.
 */
const PIPELINE_REVEAL_ITEMS = [
  { label: "researching your city...", detail: "venue scout" },
  { label: "generating backstory candidates...", detail: "scenario writer" },
  { label: "compiling first message...", detail: "opening salvo" },
]

export interface PipelineGateProps extends StepProps {
  userId: string
}

function buildProfileRequest(
  v: StepProps["values"]
): OnboardingV2ProfileRequest {
  return {
    location_city: v.location_city ?? "",
    social_scene: (v.social_scene ?? "techno") as SocialScene,
    drug_tolerance: v.drug_tolerance ?? 3,
    life_stage: (v.life_stage ?? null) as LifeStage | null,
    interest: v.interest ?? null,
    phone: v.phone ?? null,
    name: v.name ?? null,
    age: v.age ?? null,
    occupation: v.occupation ?? null,
    wizard_step: 10,
  }
}

/**
 * Resolve `useReducedMotion` via the `in` operator — routes through the
 * mock Proxy's `has` trap (not `get`), sidestepping vitest's strict-mock
 * throw on undeclared exports. See DossierStamp for the sibling pattern.
 */
type FramerReducedMotionHook = () => boolean | null

function resolveFramerReducedMotionHook(): FramerReducedMotionHook | null {
  try {
    if ("useReducedMotion" in FramerMotion) {
      const hook = (FramerMotion as { useReducedMotion?: unknown }).useReducedMotion
      if (typeof hook === "function") return hook as FramerReducedMotionHook
    }
  } catch {
    /* strict-mock proxy threw — fall through to null */
  }
  return null
}

const framerReducedMotionHook = resolveFramerReducedMotionHook()

function useReducedMotionCompat(): boolean {
  if (framerReducedMotionHook !== null) {
    // eslint-disable-next-line react-hooks/rules-of-hooks -- stable per-env
    return !!framerReducedMotionHook()
  }
  return false
}

export function PipelineGate({ values, onAdvance, userId }: PipelineGateProps) {
  const api = useOnboardingAPI()
  const reducedMotion = useReducedMotionCompat()
  const submittedRef = useRef(false)
  const [pollIntervalMs, setPollIntervalMs] = useState<number>(DEFAULT_POLL_INTERVAL_MS)
  const [maxWaitMs, setMaxWaitMs] = useState<number>(DEFAULT_MAX_WAIT_MS)
  const [pollEnabled, setPollEnabled] = useState<boolean>(false)
  const [submitError, setSubmitError] = useState<"none" | "409" | "422">("none")
  const [elapsedLate, setElapsedLate] = useState(false)
  const copy = WIZARD_COPY.pipelineGate

  // One-shot submit on mount
  useEffect(() => {
    if (submittedRef.current) return
    submittedRef.current = true
    api
      .submitProfile(buildProfileRequest(values))
      .then((resp) => {
        if (resp.poll_interval_seconds) {
          setPollIntervalMs(Math.round(resp.poll_interval_seconds * 1000))
        }
        if (resp.poll_max_wait_seconds) {
          setMaxWaitMs(Math.round(resp.poll_max_wait_seconds * 1000))
        }
        setPollEnabled(true)
      })
      .catch((err: unknown) => {
        if (typeof err === "object" && err !== null && "status" in err) {
          const status = (err as { status: unknown }).status
          if (status === 409) {
            setSubmitError("409")
            return
          }
        }
        setSubmitError("422")
      })
  }, [api, values])

  const pipeline = useOnboardingPipelineReady({
    userId,
    enabled: pollEnabled,
    pollIntervalMs,
    maxWaitMs,
  })

  // Late-copy switch (spec FR-5 state table: >=15s → "Almost there...")
  useEffect(() => {
    if (!pollEnabled) return
    const tid = setTimeout(() => setElapsedLate(true), LATE_COPY_THRESHOLD_MS)
    return () => clearTimeout(tid)
  }, [pollEnabled])

  // Auto-advance when the gate settles into a terminal UI state.
  const terminal =
    pipeline.state === "ready" ||
    pipeline.state === "degraded" ||
    pipeline.state === "failed" ||
    pipeline.timedOut
  useEffect(() => {
    if (!terminal) return
    const tid = setTimeout(() => {
      onAdvance({})
    }, AUTO_ADVANCE_DELAY_MS)
    return () => clearTimeout(tid)
  }, [terminal, onAdvance])

  // Derive which stamp to render.
  let stampKind: StampKind = "pending"
  if (pipeline.state === "ready") stampKind = "ready"
  else if (pipeline.state === "degraded" || pipeline.state === "failed") {
    stampKind = "degraded"
  } else if (pipeline.timedOut) stampKind = "timeout"

  const stampVariant =
    stampKind === "ready"
      ? "cleared"
      : stampKind === "pending"
      ? "clearance-pending"
      : "provisional"

  // Map pipeline signals to DossierReveal rows (design-brief teaching #3).
  // Venue research status contributes row 1; backstoryAvailable row 2; the
  // third row lands the instant state flips to ready/degraded/timeout/failed
  // (the "compiling first message" signal is opaque — treat terminal as
  // implicit completion).
  let revealedCount = 0
  if (
    pipeline.venueResearchStatus === "complete" ||
    pipeline.venueResearchStatus === "cache_hit"
  ) {
    revealedCount = Math.max(revealedCount, 1)
  }
  if (pipeline.backstoryAvailable) revealedCount = Math.max(revealedCount, 2)
  if (terminal) revealedCount = PIPELINE_REVEAL_ITEMS.length
  if (reducedMotion) revealedCount = PIPELINE_REVEAL_ITEMS.length

  // 409 rewind hint — orchestrator listens for data-testid="pipeline-gate-409"
  // and rewinds to step 9.
  if (submitError === "409") {
    return (
      <section
        data-testid="wizard-step-10"
        className="relative min-h-screen overflow-hidden bg-void"
      >
        <FallingPattern />
        <AuroraOrbs />
        <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
          <div className="w-full max-w-2xl flex flex-col gap-8">
            <WizardProgress current={7} total={7} />
            <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
              <p
                data-testid="pipeline-gate-409"
                className="text-sm text-primary font-black tracking-widest uppercase"
              >
                {copy.failedToast}
              </p>
            </div>
          </div>
        </div>
      </section>
    )
  }

  if (submitError === "422") {
    return (
      <section
        data-testid="wizard-step-10"
        className="relative min-h-screen overflow-hidden bg-void"
      >
        <FallingPattern />
        <AuroraOrbs />
        <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
          <div className="w-full max-w-2xl flex flex-col gap-8">
            <WizardProgress current={7} total={7} />
            <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
              <p className="text-sm text-primary font-black tracking-widest uppercase">
                {copy.failedToast}
              </p>
            </div>
          </div>
        </div>
      </section>
    )
  }

  // The stamp text IS the hero headline on this step — rendering a
  // separate `<h1>{copy.headline}</h1>` AND a DossierStamp with the same
  // string produces two nodes with identical text, breaking RTL's
  // single-match queries (spec test "shows the PENDING stamp..." asserts
  // `getByText(copy.headline)` returns a unique node). The stamp wrapper
  // carries the `<h1>` role so screen-reader hierarchy is preserved.
  return (
    <section
      data-testid="wizard-step-10"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-2xl flex flex-col items-center gap-8 text-center">
          <WizardProgress current={7} total={7} />

          <h1
            data-testid="pipeline-gate-stamp"
            data-state={stampKind}
            className="inline-block text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none"
          >
            <DossierStamp state={stampVariant} />
          </h1>

          <p
            role="status"
            aria-live="polite"
            className="text-lg text-muted-foreground max-w-md leading-relaxed"
          >
            {elapsedLate ? copy.subLate : copy.subEarly}
          </p>

          <DossierReveal
            items={PIPELINE_REVEAL_ITEMS}
            revealedCount={revealedCount}
            prompt="pipeline --status"
            className="w-full max-w-md"
          />
        </div>
      </div>
    </section>
  )
}
