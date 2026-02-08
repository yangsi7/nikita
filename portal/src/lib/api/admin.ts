import { api } from "./client"
import type {
  AdminUser, AdminUserDetail, AdminStats, PipelineHealth,
  PromptDetail, ProcessingStats, PipelineRun,
  AdminConversationsResponse, GeneratedPromptsResponse,
  EngagementData, VicePreference, Conversation, ConversationDetail,
} from "./types"

export const adminApi = {
  // Stats — backend returns AdminStatsResponse (total_users, active_users, etc.)
  getStats: () => api.get<AdminStats>("/admin/stats"),

  // Pipeline health — unified pipeline (Spec 042)
  // Falls back gracefully if endpoint not yet deployed
  getPipelineHealth: () => api.get<PipelineHealth>("/admin/unified-pipeline/health"),

  // Users — backend returns list[AdminUserListItem] (plain array, NOT paginated)
  getUsers: (params?: { search?: string; chapter?: number; engagement?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set("page", String(params.page))
    if (params?.page_size) searchParams.set("page_size", String(params.page_size))
    const qs = searchParams.toString()
    return api.get<AdminUser[]>(`/admin/users${qs ? `?${qs}` : ""}`)
  },
  getUser: (id: string) => api.get<AdminUserDetail>(`/admin/users/${id}`),
  getUserMetrics: (id: string) => api.get<{ intimacy: number; passion: number; trust: number; secureness: number; weights: Record<string, number> }>(`/admin/users/${id}/metrics`),
  getUserEngagement: (id: string) => api.get<EngagementData>(`/admin/users/${id}/engagement`),
  getUserVices: (id: string) => api.get<VicePreference[]>(`/admin/users/${id}/vices`),
  getUserConversations: (id: string, page = 1) =>
    api.get<{ conversations: Conversation[]; total_count: number; page: number; page_size: number }>(`/admin/users/${id}/conversations?page=${page}`),
  getUserConversation: (userId: string, convId: string) =>
    api.get<ConversationDetail>(`/portal/conversations/${convId}`),
  getUserScores: (id: string, days = 7) =>
    api.get<{ user_id: string; current_score: number; chapter: number; points: Array<{ timestamp: string; score: number; chapter: number; event_type: string }>; days: number }>(`/admin/users/${id}/scores?days=${days}`),

  // Mutations
  setScore: (id: string, score: number, reason: string) =>
    api.put<void>(`/admin/users/${id}/score`, { score, reason }),
  setChapter: (id: string, chapter: number, reason: string) =>
    api.put<void>(`/admin/users/${id}/chapter`, { chapter, reason }),
  setStatus: (id: string, status: string, reason: string) =>
    api.put<void>(`/admin/users/${id}/status`, { game_status: status, reason }),
  setEngagement: (id: string, state: string, reason: string) =>
    api.put<void>(`/admin/users/${id}/engagement`, { state, reason }),
  resetBoss: (id: string) =>
    api.post<void>(`/admin/users/${id}/reset-boss`),
  clearEngagement: (id: string) =>
    api.post<void>(`/admin/users/${id}/clear-engagement`),
  setMetrics: (id: string, metrics: { intimacy?: number; passion?: number; trust?: number; secureness?: number; reason: string }) =>
    api.put<void>(`/admin/users/${id}/metrics`, metrics),
  triggerPipeline: (id: string, conversationId?: string) =>
    api.post<{ job_id: string | null; status: string; message: string }>(`/admin/users/${id}/trigger-pipeline`, conversationId ? { conversation_id: conversationId } : {}),
  getPipelineHistory: (id: string) =>
    api.get<{ items: PipelineRun[]; total_count: number; page: number; page_size: number }>(`/admin/users/${id}/pipeline-history`),

  // Conversations — backend has /admin/conversations with platform filter
  getVoiceConversations: (params?: { user_id?: string; page?: number }) => {
    const searchParams = new URLSearchParams()
    searchParams.set("platform", "voice")
    if (params?.user_id) searchParams.set("user_id", params.user_id)
    if (params?.page) searchParams.set("page", String(params.page))
    return api.get<AdminConversationsResponse>(`/admin/conversations?${searchParams.toString()}`)
  },
  getTextConversations: (params?: { user_id?: string; page?: number }) => {
    const searchParams = new URLSearchParams()
    searchParams.set("platform", "telegram")
    if (params?.user_id) searchParams.set("user_id", params.user_id)
    if (params?.page) searchParams.set("page", String(params.page))
    return api.get<AdminConversationsResponse>(`/admin/conversations?${searchParams.toString()}`)
  },

  // Prompts — backend returns { prompts: [], total_count, page, page_size }
  getPrompts: (page = 1) => api.get<GeneratedPromptsResponse>(`/admin/prompts?page=${page}`),
  getPrompt: (id: string) => api.get<PromptDetail>(`/admin/prompts/${id}`),

  // Jobs — backend returns ProcessingStatsResponse (single object)
  getProcessingStats: () => api.get<ProcessingStats>("/admin/processing-stats"),
  triggerJob: (jobName: string) => api.post<void>(`/tasks/${jobName}`),
}
