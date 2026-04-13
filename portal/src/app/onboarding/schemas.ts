import { z } from "zod"

export const VALID_SCENES = ["techno", "art", "food", "cocktails", "nature"] as const
export const VALID_LIFE_STAGES = ["tech", "finance", "creative", "student", "entrepreneur", "other"] as const

// E.164 international phone number pattern (Spec 212, PR A)
// Current value: /^\+[1-9][0-9]{7,19}$/ — min 8 chars (+CC+7digits), max 20 chars
// Prior: not present. Added in GH #199 / Spec 212.
// Rationale: E.164 is the universal portable format; empty string means "skipped"
const E164_PHONE_REGEX = /^\+[1-9][0-9]{7,19}$/

export const profileSchema = z.object({
  location_city: z.string().min(2, "Please enter your city").max(100, "City name too long"),
  social_scene: z.enum(VALID_SCENES, {
    error: "Pick a scene that speaks to you",
  }),
  drug_tolerance: z.number().int().min(1, "Must be at least 1").max(5, "Must be at most 5"),
  life_stage: z.enum(VALID_LIFE_STAGES).optional(),
  interest: z.string().max(200, "Interest too long").optional(),
  // Phone is optional: empty string means user skipped; non-empty must be valid E.164
  phone: z
    .union([
      z.literal(""),
      z
        .string()
        .regex(E164_PHONE_REGEX, "Enter a valid international number starting with +")
        .min(8)
        .max(20),
    ])
    .optional()
    .default(""),
})

export type ProfileFormValues = z.infer<typeof profileSchema>
