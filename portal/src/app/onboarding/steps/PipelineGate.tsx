"use client"

/**
 * PipelineGate — Step 10 of the wizard.
 *
 * Spec 214 FR-5 + FR-7. Posts the full profile on mount (once), polls
 * /pipeline-ready via `useOnboardingPipelineReady`, and renders the stamp
 * with a `data-state` attribute so Playwright can wait for the terminal
 * state without networkidle.
 *
 * Full-viewport landing-page aesthetic via StepShell. Renders the
 * DossierReveal pipeline-stage panel driven by pipeline state (teaching
 * moment #3 from the design brief) — each completed stage adds a ✓ line,
 * then the CLEARED stamp lands on ready.
 *
 * State machine → stamp map (`data-testid="pipeline-gate-stamp"` always
 * renders so Playwright can assert by `data-state` value):
 *   pending    → state="pending"   / SETTING UP... (pulsing)
 *   ready      → state="ready"     / CLEARED + auto-advance after 1.5s
 *   degraded   → state="degraded"  / PROVISIONAL — READY + auto-advance
 *   timed out  → state="timeout"   / PROVISIONAL — READY + advance
 *   submit 422 → state="failed"    / "VALIDATION FAILED" + copy
 *   submit 409 → state="conflict"  / "CACHE STALE — RETRY" + copy
 */

import { useEffect, useRef, useState } from "react"

import { StepShell } from "@/app/onboarding/components/StepShell"
import { DossierStamp } from "@/app/onboarding/components/DossierStamp"
import { DossierReveal } from "@/app/onboarding/components/DossierReveal"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { useReducedMotionCompat } from "@/app/onboarding/hooks/use-reduced-motion-compat"
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

type StampKind = "pending" | "ready" | "degraded" | "timeout" | "failed" | "conflict"

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

  // Auto-advance when the gate settles into a terminal UI state. 422/409
  // DO NOT auto-advance — the orchestrator handles them.
  const terminal =
    submitError === "none" &&
    (pipeline.state === "ready" ||
      pipeline.state === "degraded" ||
      pipeline.state === "failed" ||
      pipeline.timedOut)
  useEffect(() => {
    if (!terminal) return
    const tid = setTimeout(() => {
      onAdvance({})
    }, AUTO_ADVANCE_DELAY_MS)
    return () => clearTimeout(tid)
  }, [terminal, onAdvance])

  // Derive which stamp to render. Submit errors win over pipeline state.
  let stampKind: StampKind = "pending"
  if (submitError === "422") stampKind = "failed"
  else if (submitError === "409") stampKind = "conflict"
  else if (pipeline.state === "ready") stampKind = "ready"
  else if (pipeline.state === "degraded" || pipeline.state === "failed") {
    stampKind = "degraded"
  } else if (pipeline.timedOut) stampKind = "timeout"

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

  // 409 — terminal conflict (orchestrator listens via data-testid="pipeline-gate-409"
  // to rewind to step 9). Stamp carries data-state="conflict" so Playwright
  // can assert on the stamp uniformly across all terminal states.
  if (submitError === "409") {
    return (
      <StepShell testId="wizard-step-10">
        <WizardProgress current={7} total={7} />
        <div className="flex flex-col items-center gap-6 text-center">
          <h1
            data-testid="pipeline-gate-stamp"
            data-state="conflict"
            className="inline-block text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none"
          >
            <span className="text-primary font-black tracking-widest uppercase">
              CACHE STALE — RETRY
            </span>
          </h1>
          <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
            <p
              data-testid="pipeline-gate-409"
              className="text-sm text-primary font-black tracking-widest uppercase"
            >
              {copy.failedToast}
            </p>
          </div>
        </div>
      </StepShell>
    )
  }

  // 422 — terminal validation failure. Stamp + Nikita-voiced body.
  if (submitError === "422") {
    return (
      <StepShell testId="wizard-step-10">
        <WizardProgress current={7} total={7} />
        <div className="flex flex-col items-center gap-6 text-center">
          <h1
            data-testid="pipeline-gate-stamp"
            data-state="failed"
            className="inline-block text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none"
          >
            <span className="text-primary font-black tracking-widest uppercase">
              VALIDATION FAILED
            </span>
          </h1>
          <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
            <p className="text-sm text-primary font-black tracking-widest uppercase">
              {copy.failedToast}
            </p>
          </div>
        </div>
      </StepShell>
    )
  }

  const stampVariant =
    stampKind === "ready"
      ? "cleared"
      : stampKind === "pending"
        ? "clearance-pending"
        : "provisional"

  // The stamp text IS the hero headline on this step — rendering a
  // separate `<h1>{copy.headline}</h1>` AND a DossierStamp with the same
  // string produces two nodes with identical text, breaking RTL's
  // single-match queries (spec test "shows the PENDING stamp..." asserts
  // `getByText(copy.headline)` returns a unique node). The stamp wrapper
  // carries the `<h1>` role so screen-reader hierarchy is preserved.
  return (
    <StepShell testId="wizard-step-10">
      <WizardProgress current={7} total={7} />
      <div className="flex flex-col items-center gap-8 text-center">
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
    </StepShell>
  )
}
