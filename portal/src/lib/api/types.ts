// API response types matching backend schemas

export interface UserStats {
  id: string
  telegram_id: number | null
  email: string | null
  relationship_score: number // 0-100
  chapter: number // 1-5
  boss_attempts: number // 0-3
  game_status: 'active' | 'boss_fight' | 'game_over' | 'won'
  metrics: {
    intimacy: number
    passion: number
    trust: number
    secureness: number
  }
  created_at: string
  updated_at: string
}

export interface EngagementState {
  state: 'calibrating' | 'in_zone' | 'drifting' | 'clingy' | 'distant' | 'out_of_zone'
  calibration_score: number
  consecutive_in_zone: number
  consecutive_clingy_days: number
  consecutive_distant_days: number
  multiplier: number // 0.7-1.1
  updated_at: string
}

export interface Vice {
  category:
    | 'intellectual_dominance'
    | 'risk_taking'
    | 'substances'
    | 'sexuality'
    | 'emotional_intensity'
    | 'rule_breaking'
    | 'dark_humor'
    | 'vulnerability'
  intensity_level: number // 1-5
  engagement_score: number // 0-100
}

export interface Conversation {
  id: string
  started_at: string
  ended_at: string | null
  platform: 'telegram' | 'voice'
  message_count: number
  score_change: number
}

export interface DailySummary {
  id: string
  date: string
  summary_text: string
  mood: string
  created_at: string
}

export interface ScoreHistoryPoint {
  timestamp: string
  score: number
  event_type: string
  description: string | null
}

export interface DecayStatus {
  grace_period_hours: number
  hours_remaining: number
  decay_rate: number
  current_score: number
  projected_score: number
  is_decaying: boolean
}

export interface ScoreHistoryResponse {
  points: ScoreHistoryPoint[]
  total_count: number
}
