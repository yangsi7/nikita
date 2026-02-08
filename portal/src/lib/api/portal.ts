import { api } from "./client"
import type {
  UserStats, ScoreHistory, EngagementData, DecayStatus,
  VicePreference, Conversation, ConversationDetail,
  DailySummary, UserSettings,
} from "./types"

export const portalApi = {
  getStats: () => api.get<UserStats>("/portal/stats"),
  getScoreHistory: (days = 30) => api.get<ScoreHistory>(`/portal/score-history?days=${days}`),
  getEngagement: () => api.get<EngagementData>("/portal/engagement"),
  getDecayStatus: () => api.get<DecayStatus>("/portal/decay"),
  getVices: () => api.get<VicePreference[]>("/portal/vices"),
  getConversations: (page = 1, pageSize = 10) =>
    api.get<{ conversations: Conversation[]; total: number }>(
      `/portal/conversations?page=${page}&page_size=${pageSize}`
    ),
  getConversation: (id: string) =>
    api.get<ConversationDetail>(`/portal/conversations/${id}`),
  getDailySummaries: (limit = 14) =>
    api.get<DailySummary[]>(`/portal/daily-summaries?limit=${limit}`),
  getSettings: () => api.get<UserSettings>("/portal/settings"),
  updateSettings: (data: Partial<UserSettings>) =>
    api.put<UserSettings>("/portal/settings", data),
  linkTelegram: () => api.post<{ code: string }>("/portal/link-telegram"),
  deleteAccount: () => api.delete<void>("/portal/account"),
}
