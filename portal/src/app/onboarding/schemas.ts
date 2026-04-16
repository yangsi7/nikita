import { z } from "zod"

export const VALID_SCENES = ["techno", "art", "food", "cocktails", "nature"] as const
export const VALID_LIFE_STAGES = ["tech", "finance", "creative", "student", "entrepreneur", "other"] as const

// E.164 international phone number pattern (Spec 212, PR #266)
// Current value: /^\+[1-9][0-9]{7,19}$/ — min 8 chars (+CC+7digits), max 20 chars
// Prior: not present. Added in Spec 212 / PR #266.
// Rationale: E.164 is the universal portable format; empty string means "skipped"
export const E164_PHONE_REGEX = /^\+[1-9][0-9]{7,19}$/

// Spec 214 FR-7 (identity step) + NR-2 (validation).
// Minimum legal age — matches backend onboarding facade guard.
// Current value: 18
// Prior: not present. Added in Spec 214 / PR 214-C (T310).
// Rationale: matches existing `users.age >= 18` check; TOS alignment.
export const MIN_AGE = 18

// Spec 214 FR-1 (11-step wizard) + FR-10.2 (wizard_step passthrough).
// Range of valid wizard steps that persist to `onboarding_profile.wizard_step`.
// Step 1-2 are pre-wizard (landing + auth); steps 3-11 are the dossier wizard.
// The backend contract (`PipelineReadyResponse.wizard_step`) uses `ge=1, le=11`
// so the client matches that envelope to stay round-trip compatible.
// Current values: MIN=1, MAX=11
// Prior: not present. Added in Spec 214 / PR 214-C (T310).
export const WIZARD_STEP_MIN = 1
export const WIZARD_STEP_MAX = 11

export const profileSchema = z.object({
  location_city: z.string().min(2, "Please enter your city").max(100, "City name too long"),
  social_scene: z.enum(VALID_SCENES, {
    error: "Pick a scene that speaks to you",
  }),
  drug_tolerance: z.number().int().min(1, "Must be at least 1").max(5, "Must be at most 5"),
  life_stage: z.enum(VALID_LIFE_STAGES).optional(),
  interest: z.string().max(200, "Interest too long").optional(),
  // Phone is optional: empty string = skipped, non-empty must match E.164
  phone: z
    .string()
    .default("")
    .refine(
      (val) => val === "" || E164_PHONE_REGEX.test(val),
      "Enter a valid international number starting with +"
    ),
  // Spec 214 FR-7: identity dossier fields (name/age/occupation). All three
  // are optional at the step level (users may skip identity), but when
  // supplied must meet these bounds. The wizard's step-7 form enforces
  // per-field; the aggregate submit uses `.partial()` for leniency.
  name: z.string().min(1, "She wants to know what to call you.").optional(),
  age: z
    .number()
    .int("Whole years only.")
    .min(MIN_AGE, `Must be at least ${MIN_AGE}.`)
    .optional(),
  occupation: z
    .string()
    .min(1, "She'll ask what you do. Give her something.")
    .optional(),
  // Spec 214 FR-10.2: last completed wizard step, passes through to the
  // backend `PipelineReadyResponse.wizard_step` for cross-device resume.
  wizard_step: z
    .number()
    .int()
    .min(WIZARD_STEP_MIN)
    .max(WIZARD_STEP_MAX)
    .optional(),
})

export type ProfileFormValues = z.infer<typeof profileSchema>
