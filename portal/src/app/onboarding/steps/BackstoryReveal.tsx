"use client"

/**
 * BackstoryReveal — Step 8 of the wizard.
 *
 * Spec 214 FR-4 + FR-9. Calls POST /onboarding/preview-backstory once on
 * mount, renders three scenario cards in a WAI-ARIA radiogroup, and commits
 * the selection via PUT /profile/chosen-option on CTA.
 *
 * Full-viewport landing-page aesthetic via StepShell (bg-void +
 * FallingPattern + AuroraOrbs + EASE_OUT_QUART step-entry animation).
 *
 * Paths handled:
 *   - Loading: dossier loading copy, CLEARANCE: PENDING stamp.
 *   - Success: 3 cards, click to select (CONFIRMED stamp on selected),
 *             CTA fires selectBackstory + advance with
 *             { chosen_option_id, cache_key }.
 *   - Degraded: empty scenarios OR degraded=true → ANALYSIS: PENDING stamp
 *              and advance on "Understood."
 *   - 429: show the canonical "Too eager. Wait a moment." message.
 *
 * Radiogroup keyboard interaction (AC-9.4, WAI-ARIA radiogroup pattern):
 *   - ArrowDown / ArrowRight → focus next card (wraps).
 *   - ArrowUp / ArrowLeft    → focus previous card (wraps).
 *   - Home                    → focus first card.
 *   - End                     → focus last card.
 *   - Space / Enter           → select the focused card.
 * A roving tabindex keeps exactly ONE card in the tab order at any time.
 */

import { useEffect, useRef, useState, type KeyboardEvent } from "react"

import { Button } from "@/components/ui/button"
import { StepShell } from "@/app/onboarding/components/StepShell"
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

export function BackstoryReveal({ values, onAdvance }: StepProps) {
  const api = useOnboardingAPI()
  const [phase, setPhase] = useState<Phase>({ kind: "loading" })
  const [selectedId, setSelectedId] = useState<string | null>(
    values.chosen_option_id ?? null
  )
  const [focusedIndex, setFocusedIndex] = useState<number>(0)
  const [submitting, setSubmitting] = useState(false)
  const fetchedRef = useRef(false)
  const cardRefs = useRef<Array<HTMLDivElement | null>>([])
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
    if (phase.kind === "ready") {
      const target = cardRefs.current[0]
      if (target) target.focus()
    }
  }, [phase.kind])

  if (phase.kind === "loading") {
    return (
      <StepShell testId="wizard-step-8" contentMaxWidthClass="max-w-3xl">
        <WizardProgress current={6} total={7} />
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
      </StepShell>
    )
  }

  if (phase.kind === "rate-limited") {
    return (
      <StepShell testId="wizard-step-8" contentMaxWidthClass="max-w-3xl">
        <WizardProgress current={6} total={7} />
        <div className="rounded-xl border border-glass-border bg-glass p-8 text-center backdrop-blur-md">
          <p className="text-sm text-primary font-black tracking-widest uppercase">
            {copy.rateLimitError}
          </p>
        </div>
      </StepShell>
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
      <StepShell testId="wizard-step-8" contentMaxWidthClass="max-w-3xl">
        <WizardProgress current={6} total={7} />
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
            className="text-primary-foreground font-black tracking-[0.2em] uppercase"
          >
            {copy.ctaDegraded}
          </Button>
        </div>
      </StepShell>
    )
  }

  // phase.kind === "ready"
  const { scenarios, cacheKey } = phase

  const confirmAndAdvance = async () => {
    if (!selectedId || submitting) return
    setSubmitting(true)
    try {
      // GH #313 (CRITICAL) fix. PATCH the full collected profile to JSONB
      // BEFORE calling selectBackstory so the backend's clearance check
      // (which recomputes compute_backstory_cache_key from the persisted
      // user.onboarding_profile) sees the same values that went into the
      // client-side cache_key it is about to receive. Without this, the
      // JSONB stays empty, the server recomputes `unknown|unknown|...`,
      // and the submitted key `<city>|<scene>|...` mismatches, returning
      // 403 "Clearance mismatch. Start over." (2026-04-17 Agent H dogfood
      // walk). Sending every field the cache_key depends on; undefined
      // fields are dropped by fetch JSON serialization and treated as
      // "not-set" by the backend PATCH handler.
      await api.patchProfile({
        location_city: values.location_city ?? undefined,
        social_scene: values.social_scene ?? undefined,
        drug_tolerance: values.drug_tolerance ?? undefined,
        life_stage: values.life_stage ?? undefined,
        interest: values.interest ?? undefined,
        name: values.name ?? undefined,
        age: values.age ?? undefined,
        occupation: values.occupation ?? undefined,
        wizard_step: 8,
      })
      await api.selectBackstory(selectedId, cacheKey)
      onAdvance({ chosen_option_id: selectedId, cache_key: cacheKey })
    } catch {
      // Retry is user-driven per AC-9.2 (both PATCH and PUT are idempotent).
      // On failure (either endpoint), re-enable the CTA and let the user
      // click again. Do NOT call onAdvance — we must not race forward past
      // a half-persisted state.
      setSubmitting(false)
    }
  }

  /**
   * Roving tabindex: whichever card matches `focusedIndex` (or the
   * selected card, if any) is the one card carrying `tabIndex={0}`. All
   * others are `tabIndex={-1}` so Tab leaves the group after one stop.
   */
  const rovingIndex =
    selectedId !== null
      ? Math.max(
          0,
          scenarios.findIndex((s) => s.id === selectedId)
        )
      : focusedIndex

  const focusCard = (nextIndex: number) => {
    const wrapped = ((nextIndex % scenarios.length) + scenarios.length) % scenarios.length
    setFocusedIndex(wrapped)
    const target = cardRefs.current[wrapped]
    if (target) target.focus()
  }

  const handleRadiogroupKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    switch (e.key) {
      case "ArrowDown":
      case "ArrowRight":
        e.preventDefault()
        focusCard(rovingIndex + 1)
        break
      case "ArrowUp":
      case "ArrowLeft":
        e.preventDefault()
        focusCard(rovingIndex - 1)
        break
      case "Home":
        e.preventDefault()
        focusCard(0)
        break
      case "End":
        e.preventDefault()
        focusCard(scenarios.length - 1)
        break
      case " ":
      case "Enter":
        e.preventDefault()
        setSelectedId(scenarios[rovingIndex].id)
        break
      default:
        break
    }
  }

  return (
    <StepShell testId="wizard-step-8" contentMaxWidthClass="max-w-3xl">
      <WizardProgress current={6} total={7} />
      <header className="space-y-3">
        <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
          {copy.readyHeadline}
        </h1>
      </header>

      <div
        role="radiogroup"
        aria-label="Backstory scenarios"
        className="space-y-4"
        onKeyDown={handleRadiogroupKeyDown}
      >
        {scenarios.map((scenario, i) => {
          const selected = selectedId === scenario.id
          const header = copy.cardHeaders[i] ?? `SCENARIO ${i + 1}`
          return (
            <div
              key={scenario.id}
              ref={(el) => {
                cardRefs.current[i] = el
              }}
              role="radio"
              tabIndex={i === rovingIndex ? 0 : -1}
              aria-checked={selected}
              onClick={() => {
                setSelectedId(scenario.id)
                setFocusedIndex(i)
              }}
              onFocus={() => setFocusedIndex(i)}
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
          className="text-primary-foreground font-black tracking-[0.2em] uppercase"
        >
          {copy.ctaCards}
        </Button>
      </div>
    </StepShell>
  )
}
