export const CHAPTER_NAMES: Record<number, string> = {
  1: "The Spark",
  2: "Getting Closer",
  3: "The Deep End",
  4: "Fire & Ice",
  5: "All or Nothing",
}

export const CHAPTER_ROMAN: Record<number, string> = {
  1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
}

export const ENGAGEMENT_STATES = [
  "CALIBRATING", "IN_ZONE", "DRIFTING", "CLINGY", "DISTANT", "OUT_OF_ZONE",
] as const

export const GAME_STATUSES = [
  "active", "boss_fight", "game_over", "won",
] as const

export const PIPELINE_STAGES = [
  "extraction", "memory_update", "life_sim", "emotional",
  "game_state", "conflict", "touchpoint", "summary", "prompt_builder",
] as const

// Use empty string in production so requests go through Vercel rewrites (no CORS)
// Only use NEXT_PUBLIC_API_URL for local development pointing to localhost:8000
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ""

export const STALE_TIMES = {
  stats: 30_000,
  history: 60_000,
  settings: 300_000,
  admin: 15_000,
} as const
