import { api } from "./client"
import type {
  AdminUser, AdminUserDetail, AdminStats, PipelineHealth,
  VoiceConversation, PromptRecord, PromptDetail,
  JobStatus, PipelineRun, PaginatedResponse,
  EngagementData, VicePreference, Conversation,
  ConversationDetail, ScoreHistory,
} from "./types"

export const adminApi = {
  // Stats
  getStats: () => api.get<AdminStats>("/admin/stats"),
  getPipelineHealth: () => api.get<PipelineHealth>("/admin/unified-pipeline/health"),

  // Users
  getUsers: (params?: { search?: string; chapter?: number; engagement?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.search) searchParams.set("search", params.search)
    if (params?.chapter) searchParams.set("chapter", String(params.chapter))
    if (params?.engagement) searchParams.set("engagement_state", params.engagement)
    if (params?.page) searchParams.set("page", String(params.page))
    if (params?.page_size) searchParams.set("page_size", String(params.page_size))
    const qs = searchParams.toString()
    return api.get<PaginatedResponse<AdminUser>>(`/admin/users${qs ? `?${qs}` : ""}`)
  },
  getUser: (id: string) => api.get<AdminUserDetail>(`/admin/users/${id}`),
  getUserMetrics: (id: string) => api.get<AdminUserDetail["metrics"]>(`/admin/users/${id}/metrics`),
  getUserEngagement: (id: string) => api.get<EngagementData>(`/admin/users/${id}/engagement`),
  getUserVices: (id: string) => api.get<VicePreference[]>(`/admin/users/${id}/vices`),
  getUserConversations: (id: string) => api.get<Conversation[]>(`/admin/users/${id}/conversations`),
  getUserConversation: (userId: string, convId: string) =>
    api.get<ConversationDetail>(`/admin/users/${userId}/conversations/${convId}`),
  getUserScores: (id: string) => api.get<ScoreHistory>(`/admin/users/${id}/scores`),

  // Mutations
  setScore: (id: string, score: number, reason: string) =>
    api.put<void>(`/admin/users/${id}/score`, { score, reason }),
  setChapter: (id: string, chapter: number, reason: string) =>
    api.put<void>(`/admin/users/${id}/chapter`, { chapter, reason }),
  setStatus: (id: string, status: string, reason: string) =>
    api.put<void>(`/admin/users/${id}/status`, { status, reason }),
  setEngagement: (id: string, state: string, reason: string) =>
    api.put<void>(`/admin/users/${id}/engagement`, { state, reason }),
  resetBoss: (id: string, reason: string) =>
    api.post<void>(`/admin/users/${id}/reset-boss`, { reason }),
  clearEngagement: (id: string, reason: string) =>
    api.post<void>(`/admin/users/${id}/clear-engagement`, { reason }),
  setMetrics: (id: string, metrics: { intimacy?: number; passion?: number; trust?: number; secureness?: number; reason: string }) =>
    api.put<void>(`/admin/users/${id}/metrics`, metrics),
  triggerPipeline: (id: string, reason: string) =>
    api.post<{ job_id: string; status: string }>(`/admin/users/${id}/trigger-pipeline`, { reason }),
  getPipelineHistory: (id: string) =>
    api.get<PipelineRun[]>(`/admin/users/${id}/pipeline-history`),

  // Voice
  getVoiceConversations: (params?: { user_id?: string; page?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.user_id) searchParams.set("user_id", params.user_id)
    if (params?.page) searchParams.set("page", String(params.page))
    const qs = searchParams.toString()
    return api.get<PaginatedResponse<VoiceConversation>>(`/admin/voice/conversations${qs ? `?${qs}` : ""}`)
  },
  getVoiceConversation: (id: string) =>
    api.get<VoiceConversation>(`/admin/voice/conversations/${id}`),

  // Text
  getTextConversations: (params?: { user_id?: string; page?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.user_id) searchParams.set("user_id", params.user_id)
    if (params?.page) searchParams.set("page", String(params.page))
    const qs = searchParams.toString()
    return api.get<PaginatedResponse<Conversation>>(`/admin/text/conversations${qs ? `?${qs}` : ""}`)
  },

  // Prompts
  getPrompts: (page = 1) => api.get<PaginatedResponse<PromptRecord>>(`/admin/prompts?page=${page}`),
  getPrompt: (id: string) => api.get<PromptDetail>(`/admin/prompts/${id}`),

  // Jobs
  getProcessingStats: () => api.get<JobStatus[]>("/admin/processing-stats"),
  triggerJob: (jobName: string) => api.post<void>(`/tasks/${jobName}`),
}
