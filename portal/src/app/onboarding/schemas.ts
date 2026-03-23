import { z } from "zod"

export const VALID_SCENES = ["techno", "art", "food", "cocktails", "nature"] as const
export const VALID_LIFE_STAGES = ["tech", "finance", "creative", "student", "entrepreneur", "other"] as const

export const profileSchema = z.object({
  location_city: z.string().min(2, "Please enter your city").max(100, "City name too long"),
  social_scene: z.enum(VALID_SCENES, {
    error: "Pick a scene that speaks to you",
  }),
  drug_tolerance: z.number().int().min(1, "Must be at least 1").max(5, "Must be at most 5"),
  life_stage: z.enum(VALID_LIFE_STAGES).optional(),
  interest: z.string().max(200, "Interest too long").optional(),
})

export type ProfileFormValues = z.infer<typeof profileSchema>
