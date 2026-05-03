/**
 * Hobby chip taxonomy — 100 chips across 10 categories per AC C1.6.
 *
 * Per-category lists are placeholders pending UX review (Open Question Q1
 * in subspec 216-C). Master taxonomy structure (10 cat × 10 chips) is
 * locked.
 */

export interface HobbyChip {
  /** Lowercase slug — what the wizard sends back as the slot value. */
  value: string
  /** Display label. */
  label: string
  /** Category for grouping. */
  category: HobbyCategory
}

export type HobbyCategory =
  | "Music"
  | "Movement"
  | "Gaming"
  | "Reading"
  | "Food & Drink"
  | "Travel"
  | "Art & Making"
  | "Tech & Gear"
  | "Outdoors & Nature"
  | "Social & Nightlife"

export const HOBBY_CATEGORIES: readonly HobbyCategory[] = [
  "Music",
  "Movement",
  "Gaming",
  "Reading",
  "Food & Drink",
  "Travel",
  "Art & Making",
  "Tech & Gear",
  "Outdoors & Nature",
  "Social & Nightlife",
] as const

const c = (value: string, label: string, category: HobbyCategory): HobbyChip => ({
  value,
  label,
  category,
})

export const HOBBY_CHIPS: readonly HobbyChip[] = [
  // Music
  c("techno", "techno", "Music"),
  c("jazz", "jazz", "Music"),
  c("indie-rock", "indie rock", "Music"),
  c("classical", "classical", "Music"),
  c("hip-hop", "hip-hop", "Music"),
  c("reggae", "reggae", "Music"),
  c("ambient", "ambient", "Music"),
  c("folk", "folk", "Music"),
  c("metal", "metal", "Music"),
  c("opera", "opera", "Music"),
  // Movement
  c("running", "running", "Movement"),
  c("climbing", "climbing", "Movement"),
  c("yoga", "yoga", "Movement"),
  c("lifting", "lifting", "Movement"),
  c("swimming", "swimming", "Movement"),
  c("cycling", "cycling", "Movement"),
  c("dance", "dance", "Movement"),
  c("martial-arts", "martial arts", "Movement"),
  c("hiking", "hiking", "Movement"),
  c("pilates", "pilates", "Movement"),
  // Gaming
  c("arpg", "ARPG", "Gaming"),
  c("fps", "FPS", "Gaming"),
  c("moba", "MOBA", "Gaming"),
  c("indie-games", "indie games", "Gaming"),
  c("retro", "retro", "Gaming"),
  c("mmo", "MMO", "Gaming"),
  c("fighting", "fighting", "Gaming"),
  c("strategy", "strategy", "Gaming"),
  c("sandbox", "sandbox", "Gaming"),
  c("vr", "VR", "Gaming"),
  // Reading
  c("scifi", "sci-fi", "Reading"),
  c("fantasy", "fantasy", "Reading"),
  c("literary", "literary fiction", "Reading"),
  c("nonfiction", "nonfiction", "Reading"),
  c("philosophy", "philosophy", "Reading"),
  c("biography", "biography", "Reading"),
  c("poetry", "poetry", "Reading"),
  c("comics", "comics", "Reading"),
  c("essays", "essays", "Reading"),
  c("history", "history", "Reading"),
  // Food & Drink
  c("cooking", "cooking", "Food & Drink"),
  c("baking", "baking", "Food & Drink"),
  c("wine", "wine", "Food & Drink"),
  c("coffee", "coffee", "Food & Drink"),
  c("cocktails", "cocktails", "Food & Drink"),
  c("ramen", "ramen", "Food & Drink"),
  c("bbq", "BBQ", "Food & Drink"),
  c("vegan", "vegan", "Food & Drink"),
  c("fermenting", "fermenting", "Food & Drink"),
  c("tasting-menus", "tasting menus", "Food & Drink"),
  // Travel
  c("solo-travel", "solo travel", "Travel"),
  c("road-trips", "road trips", "Travel"),
  c("backpacking", "backpacking", "Travel"),
  c("city-breaks", "city breaks", "Travel"),
  c("beach", "beach", "Travel"),
  c("mountain", "mountain", "Travel"),
  c("luxury", "luxury", "Travel"),
  c("camping", "camping", "Travel"),
  c("trains", "trains", "Travel"),
  c("nomad", "nomad life", "Travel"),
  // Art & Making
  c("painting", "painting", "Art & Making"),
  c("photography", "photography", "Art & Making"),
  c("ceramics", "ceramics", "Art & Making"),
  c("woodwork", "woodwork", "Art & Making"),
  c("sewing", "sewing", "Art & Making"),
  c("3d-printing", "3D printing", "Art & Making"),
  c("knitting", "knitting", "Art & Making"),
  c("calligraphy", "calligraphy", "Art & Making"),
  c("film", "film making", "Art & Making"),
  c("sculpting", "sculpting", "Art & Making"),
  // Tech & Gear
  c("coding", "coding", "Tech & Gear"),
  c("hardware", "hardware", "Tech & Gear"),
  c("ai", "AI", "Tech & Gear"),
  c("audio-gear", "audio gear", "Tech & Gear"),
  c("cameras", "cameras", "Tech & Gear"),
  c("watches", "watches", "Tech & Gear"),
  c("home-automation", "home automation", "Tech & Gear"),
  c("retro-tech", "retro tech", "Tech & Gear"),
  c("mech-keyboards", "mech keyboards", "Tech & Gear"),
  c("synths", "synths", "Tech & Gear"),
  // Outdoors & Nature
  c("trail-running", "trail running", "Outdoors & Nature"),
  c("surfing", "surfing", "Outdoors & Nature"),
  c("skiing", "skiing", "Outdoors & Nature"),
  c("snowboarding", "snowboarding", "Outdoors & Nature"),
  c("kayaking", "kayaking", "Outdoors & Nature"),
  c("fishing", "fishing", "Outdoors & Nature"),
  c("birdwatching", "birdwatching", "Outdoors & Nature"),
  c("gardening", "gardening", "Outdoors & Nature"),
  c("foraging", "foraging", "Outdoors & Nature"),
  c("astronomy", "astronomy", "Outdoors & Nature"),
  // Social & Nightlife
  c("clubbing", "clubbing", "Social & Nightlife"),
  c("dinner-parties", "dinner parties", "Social & Nightlife"),
  c("concerts", "concerts", "Social & Nightlife"),
  c("festivals", "festivals", "Social & Nightlife"),
  c("bars", "bars", "Social & Nightlife"),
  c("karaoke", "karaoke", "Social & Nightlife"),
  c("board-games", "board games", "Social & Nightlife"),
  c("trivia", "trivia", "Social & Nightlife"),
  c("comedy", "stand-up comedy", "Social & Nightlife"),
  c("dance-classes", "dance classes", "Social & Nightlife"),
] as const

export const MIN_HOBBIES = 3
export const MAX_HOBBIES = 5
export const OTHER_MAX_LEN = 40
export const OTHER_WARN_LEN = 35
