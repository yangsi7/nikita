import { z } from "zod"

export const VALID_SCENES = ["techno", "art", "food", "cocktails", "nature"] as const

export const profileSchema = z.object({
  location_city: z.string().min(2, "Please enter your city"),
  social_scene: z.enum(VALID_SCENES, {
    error: "Pick a scene that speaks to you",
  }),
  drug_tolerance: z.number().int().min(1, "Must be at least 1").max(5, "Must be at most 5"),
})

export type ProfileFormValues = z.infer<typeof profileSchema>
