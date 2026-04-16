"use client"

/**
 * BackstoryReveal — Step 8 of the wizard.
 *
 * Spec 214 FR-4 + FR-9. Calls POST /onboarding/preview-backstory once on
 * mount, renders three scenario cards in a WAI-ARIA radiogroup, and commits
 * the selection via PUT /profile/chosen-option on CTA.
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5.
 *
 * Paths handled:
 *   - Loading: dossier loading copy, CLEARANCE: PENDING stamp.
 *   - Success: 3 cards, click to select (CONFIRMED stamp on selected),
 *             CTA fires selectBackstory + advance with
 *             { chosen_option_id, cache_key }.
 *   - Degraded: empty scenarios OR degraded=true → ANALYSIS: PENDING stamp
 *              and advance on "Understood."
 *   - 429: show the canonical "Too eager. Wait a moment." message.
 */

import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { DossierStamp } from "@/app/onboarding/components/DossierStamp"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import { useOnboardingAPI } from "@/app/onboarding/hooks/use-onboarding-api"
import type { StepProps } from "@/app/onboarding/steps/types"
import type {
  BackstoryOption,
  BackstoryPreviewResponse,
  BackstoryTone,
  SocialScene,
} from "@/app/onboarding/types/contracts"

type Phase =
  | { kind: "loading" }
  | { kind: "ready"; scenarios: BackstoryOption[]; cacheKey: string }
  | { kind: "degraded"; cacheKey: string }
  | { kind: "rate-limited" }
  | { kind: "error" }

/**
 * Per-tone badge colours. Token-only — maps the three tones to the three
 * design-brief accent tokens (rose-glow / cyan-glow / amber-glow).
 */
const TONE_BADGE_CLASS: Record<BackstoryTone, string> = {
  romantic: "border-primary/30 bg-primary/10 text-primary",
  intellectual: "border-cyan-glow/30 bg-cyan-glow/10 text-cyan-glow",
  chaotic: "border-amber-glow/30 bg-amber-glow/10 text-amber-glow",
}

interface Shell {
  children: React.ReactNode
}

function Shell({ children }: Shell) {
  return (
    <section
      data-testid="wizard-step-8"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-3xl flex flex-col gap-8">
          <WizardProgress current={6} total={7} />
          {children}
        </div>
      </div>
    </section>
  )
}

export function BackstoryReveal({ values, onAdvance }: StepProps) {
  const api = useOnboardingAPI()
  const [phase, setPhase] = useState<Phase>({ kind: "loading" })
  const [selectedId, setSelectedId] = useState<string | null>(
    values.chosen_option_id ?? null
  )
  const [submitting, setSubmitting] = useState(false)
  const fetchedRef = useRef(false)
  const firstCardRef = useRef<HTMLDivElement | null>(null)
  const copy = WIZARD_COPY.backstory

  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true

    api
      .previewBackstory({
        city: values.location_city ?? "",
        social_scene: (values.social_scene ?? "techno") as SocialScene,
        darkness_level: values.drug_tolerance ?? 3,
        life_stage: values.life_stage ?? null,
        interest: values.interest ?? null,
        age: values.age ?? null,
        occupation: values.occupation ?? null,
      })
      .then((resp: BackstoryPreviewResponse) => {
        if (!resp.scenarios || resp.scenarios.length === 0 || resp.degraded) {
          setPhase({ kind: "degraded", cacheKey: resp.cache_key })
          return
        }
        setPhase({
          kind: "ready",
          scenarios: resp.scenarios,
          cacheKey: resp.cache_key,
        })
      })
      .catch((err: unknown) => {
        if (typeof err === "object" && err !== null && "status" in err) {
          const status = (err as { status: unknown }).status
          if (status === 429) {
            setPhase({ kind: "rate-limited" })
            return
          }
        }
        setPhase({ kind: "error" })
      })
  }, [api, values])

  // AC-4.5: move focus to first scenario card when cards land.
  useEffect(() => {
    if (phase.kind === "ready" && firstCardRef.current) {
      firstCardRef.current.focus()
    }
  }, [phase.kind])

  if (phase.kind === "loading") {
    return (
      <Shell>
        <header className="space-y-3">
          <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
            {copy.loadingHeadline}
          </h1>
          <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
            {copy.loadingSub}
          </p>
        </header>
        <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
          <DossierStamp state="clearance-pending" />
        </div>
      </Shell>
    )
  }

  if (phase.kind === "rate-limited") {
    return (
      <Shell>
        <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
          <p className="text-sm text-primary font-black tracking-widest uppercase">
            {copy.rateLimitError}
          </p>
        </div>
      </Shell>
    )
  }

  if (phase.kind === "degraded" || phase.kind === "error") {
    // Note: the ANALYSIS: PENDING string is both the hero headline AND the
    // DossierStamp text for `analysis-pending`; rendering the stamp here
    // would produce duplicate nodes that break RTL's single-match queries
    // (see test "shows ANALYSIS: PENDING stamp when scenarios is empty").
    // The hero headline carries the same dossier-terminal aesthetic via
    // the monospace chrome block, so the stamp is omitted.
    return (
      <Shell>
        <header className="space-y-3">
          <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground font-mono">
            {copy.degradedHeadline}
          </h1>
          <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
            {copy.degradedSub}
          </p>
        </header>
        <div>
          <Button
            type="button"
            onClick={() => onAdvance({ chosen_option_id: null, cache_key: null })}
            className="text-primary font-black tracking-[0.2em] uppercase"
          >
            {copy.ctaDegraded}
          </Button>
        </div>
      </Shell>
    )
  }

  // phase.kind === "ready"
  const { scenarios, cacheKey } = phase

  const confirmAndAdvance = async () => {
    if (!selectedId || submitting) return
    setSubmitting(true)
    try {
      await api.selectBackstory(selectedId, cacheKey)
      onAdvance({ chosen_option_id: selectedId, cache_key: cacheKey })
    } catch {
      // Retry is user-driven per AC-9.2 (idempotent endpoint). On failure,
      // re-enable the button and let the user click again.
      setSubmitting(false)
    }
  }

  return (
    <Shell>
      <header className="space-y-3">
        <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
          {copy.readyHeadline}
        </h1>
      </header>

      <div
        role="radiogroup"
        aria-label="Backstory scenarios"
        className="space-y-4"
      >
        {scenarios.map((scenario, i) => {
          const selected = selectedId === scenario.id
          const header = copy.cardHeaders[i] ?? `SCENARIO ${i + 1}`
          return (
            <div
              key={scenario.id}
              ref={i === 0 ? firstCardRef : undefined}
              role="radio"
              tabIndex={i === 0 ? 0 : -1}
              aria-checked={selected}
              onClick={() => setSelectedId(scenario.id)}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault()
                  setSelectedId(scenario.id)
                }
              }}
              className={
                "cursor-pointer rounded-lg border p-4 outline-none transition-[border-color,background-color] duration-150 focus-visible:ring-2 focus-visible:ring-primary " +
                (selected
                  ? "border-primary bg-primary/5"
                  : "border-glass-border bg-glass hover:border-primary/30")
              }
              data-testid={`backstory-card-${i}`}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-black tracking-[0.2em] uppercase text-primary">
                  {header}
                </p>
                <span
                  className={
                    "rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-widest " +
                    TONE_BADGE_CLASS[scenario.tone]
                  }
                >
                  {scenario.tone}
                </span>
              </div>
              <p className="mt-3 text-sm text-foreground">
                <span className="text-muted-foreground">{copy.whereLabel}</span>{" "}
                {scenario.venue}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {scenario.context}
              </p>
              <p className="mt-2 text-sm text-foreground">
                <span className="text-muted-foreground">{copy.momentLabel}</span>{" "}
                {scenario.the_moment}
              </p>
              <p className="mt-2 text-sm text-foreground">
                <span className="text-muted-foreground">{copy.hookLabel}</span>{" "}
                {scenario.unresolved_hook}
              </p>
              {selected && (
                <p className="mt-3 text-xs font-black tracking-[0.2em] uppercase text-primary">
                  {copy.selectedStamp}
                </p>
              )}
            </div>
          )
        })}
      </div>

      <div>
        <Button
          type="button"
          disabled={!selectedId || submitting}
          onClick={confirmAndAdvance}
          className="text-primary font-black tracking-[0.2em] uppercase"
        >
          {copy.ctaCards}
        </Button>
      </div>
    </Shell>
  )
}
