import { api } from "./client"
import type {
  UserStats, ScoreHistory, EngagementData, DecayStatus,
  VicePreference, Conversation, ConversationDetail,
  DailySummary, UserSettings,
  EmotionalStateResponse, EmotionalStateHistory,
  LifeEventsResponse, ThoughtsResponse,
  NarrativeArcsResponse, SocialCircleResponse,
  DetailedScoreHistory, ThreadList,
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
  // Spec 046
  getEmotionalState: () => api.get<EmotionalStateResponse>("/portal/emotional-state"),
  getEmotionalStateHistory: (hours = 24) => api.get<EmotionalStateHistory>(`/portal/emotional-state/history?hours=${hours}`),
  getLifeEvents: (date?: string) => api.get<LifeEventsResponse>(`/portal/life-events${date ? `?date_str=${date}` : ""}`),
  getThoughts: (params?: { limit?: number; offset?: number; type?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set("limit", String(params.limit))
    if (params?.offset) searchParams.set("offset", String(params.offset))
    if (params?.type) searchParams.set("type", params.type)
    const qs = searchParams.toString()
    return api.get<ThoughtsResponse>(`/portal/thoughts${qs ? `?${qs}` : ""}`)
  },
  getNarrativeArcs: (activeOnly = true) => api.get<NarrativeArcsResponse>(`/portal/narrative-arcs?active_only=${activeOnly}`),
  getSocialCircle: () => api.get<SocialCircleResponse>("/portal/social-circle"),
  // Spec 047
  getDetailedScoreHistory: (days = 30) => api.get<DetailedScoreHistory>(`/portal/score-history/detailed?days=${days}`),
  getThreads: (params?: { status?: string; type?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.set("status", params.status)
    if (params?.type) searchParams.set("type", params.type)
    if (params?.limit) searchParams.set("limit", String(params.limit))
    const qs = searchParams.toString()
    return api.get<ThreadList>(`/portal/threads${qs ? `?${qs}` : ""}`)
  },
}
