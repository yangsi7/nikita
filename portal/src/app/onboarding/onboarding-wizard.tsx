"use client"

/**
 * OnboardingWizard — top-level orchestrator for Spec 214 wizard steps 3-11.
 *
 * Owns the in-memory form state, localStorage persistence (NR-1), state-
 * machine advance + rewind transitions, and step dispatch. Each step child
 * receives a narrow `StepProps` (values + onAdvance) plus step-specific
 * props where needed (PipelineGate userId, HandoffStep voiceCallState).
 *
 * Keeps the component file small by delegating domain logic to the
 * state machine and persistence helpers already established in PR 214-A.
 */

import { useCallback, useEffect, useRef, useState } from "react"

import {
  FIRST_WIZARD_STEP,
  canTransition,
  nextStep,
} from "@/app/onboarding/state/WizardStateMachine"
import {
  clearPersistedState,
  readPersistedState,
  writePersistedState,
} from "@/app/onboarding/state/WizardPersistence"
import type { WizardFormValues, WizardStep } from "@/app/onboarding/types/wizard"

import { DossierHeader } from "@/app/onboarding/steps/DossierHeader"
import { LocationStep } from "@/app/onboarding/steps/LocationStep"
import { SceneStep } from "@/app/onboarding/steps/SceneStep"
import { DarknessStep } from "@/app/onboarding/steps/DarknessStep"
import { IdentityStep } from "@/app/onboarding/steps/IdentityStep"
import { BackstoryReveal } from "@/app/onboarding/steps/BackstoryReveal"
import { PhoneStep } from "@/app/onboarding/steps/PhoneStep"
import { PipelineGate } from "@/app/onboarding/steps/PipelineGate"
import { HandoffStep, type VoiceCallState } from "@/app/onboarding/steps/HandoffStep"

const EMPTY_VALUES: WizardFormValues = {
  location_city: null,
  social_scene: null,
  drug_tolerance: null,
  life_stage: null,
  interest: null,
  name: null,
  age: null,
  occupation: null,
  phone: null,
  chosen_option_id: null,
  cache_key: null,
}

export interface OnboardingWizardProps {
  userId: string
}

export function OnboardingWizard({ userId }: OnboardingWizardProps) {
  const [step, setStep] = useState<WizardStep>(FIRST_WIZARD_STEP)
  const [values, setValues] = useState<WizardFormValues>(EMPTY_VALUES)
  const [voiceCallState] = useState<VoiceCallState>("idle")
  const hydratedRef = useRef(false)

  // NR-1 resume: hydrate from localStorage on mount (useEffect, never render).
  useEffect(() => {
    if (hydratedRef.current) return
    hydratedRef.current = true
    const persisted = readPersistedState(userId)
    if (!persisted) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot hydration from localStorage (NR-1)
    setStep(persisted.last_step)
    setValues({
      location_city: persisted.location_city,
      social_scene: persisted.social_scene,
      drug_tolerance: persisted.drug_tolerance,
      life_stage: persisted.life_stage,
      interest: persisted.interest,
      name: persisted.name,
      age: persisted.age,
      occupation: persisted.occupation,
      phone: persisted.phone,
      chosen_option_id: persisted.chosen_option_id,
      cache_key: persisted.cache_key,
    })
  }, [userId])

  const advance = useCallback(
    (patch: Partial<WizardFormValues>) => {
      const next = nextStep(step)
      if (next === null) return
      const transition = canTransition(step, next)
      if (!transition.ok) return
      const merged: WizardFormValues = { ...values, ...patch }
      setValues(merged)
      setStep(next)

      // AC-1.3: push a history entry on step advance so the browser back
      // button can be wired in a future iteration without a route change.
      if (typeof window !== "undefined") {
        window.history.replaceState(
          { step: next },
          "",
          window.location.pathname
        )
      }

      if (next === 11) {
        // AC-NR1.3: clear persisted state on final step (handoff).
        clearPersistedState(userId)
        return
      }

      writePersistedState({
        user_id: userId,
        last_step: next,
        location_city: merged.location_city,
        social_scene: merged.social_scene,
        drug_tolerance: merged.drug_tolerance,
        life_stage: merged.life_stage,
        interest: merged.interest,
        name: merged.name,
        age: merged.age,
        occupation: merged.occupation,
        phone: merged.phone,
        chosen_option_id: merged.chosen_option_id,
        cache_key: merged.cache_key,
        saved_at: new Date().toISOString(),
      })
    },
    [step, values, userId]
  )

  switch (step) {
    case 3:
      return <DossierHeader values={values} onAdvance={advance} />
    case 4:
      return <LocationStep values={values} onAdvance={advance} />
    case 5:
      return <SceneStep values={values} onAdvance={advance} />
    case 6:
      return <DarknessStep values={values} onAdvance={advance} />
    case 7:
      return <IdentityStep values={values} onAdvance={advance} />
    case 8:
      return <BackstoryReveal values={values} onAdvance={advance} />
    case 9:
      return <PhoneStep values={values} onAdvance={advance} />
    case 10:
      return <PipelineGate values={values} onAdvance={advance} userId={userId} />
    case 11:
      return (
        <HandoffStep
          values={values}
          onAdvance={advance}
          voiceCallState={voiceCallState}
        />
      )
    default:
      return <DossierHeader values={values} onAdvance={advance} />
  }
}
