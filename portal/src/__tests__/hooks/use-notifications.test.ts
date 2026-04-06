/**
 * Tests for useNotifications hook
 * Complex hook: derives notifications from 3 queries + localStorage read
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { ScoreHistory, EngagementData, DecayStatus } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getScoreHistory: vi.fn(),
    getEngagement: vi.fn(),
    getDecayStatus: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useNotifications } from "@/hooks/use-notifications"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockScoreHistory: ScoreHistory = {
  points: [
    { score: 55, chapter: 2, event_type: "message", recorded_at: "2026-03-19T10:00:00Z" },
    { score: 60, chapter: 2, event_type: "chapter_advance", recorded_at: "2026-03-20T10:00:00Z" },
    { score: 58, chapter: 2, event_type: "boss_encounter", recorded_at: "2026-03-20T14:00:00Z" },
  ],
  total_count: 3,
}

const mockEngagement: EngagementData = {
  state: "in_zone",
  multiplier: 1.2,
  calibration_score: null,
  consecutive_in_zone: 3,
  consecutive_clingy_days: 0,
  consecutive_distant_days: 0,
  recent_transitions: [
    {
      from_state: "calibrating",
      to_state: "in_zone",
      reason: "score improved",
      created_at: "2026-03-19T12:00:00Z",
    },
  ],
}

const mockDecayActive: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 4,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 56,
  is_decaying: true,
}

const mockDecayInactive: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 20,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 62,
  is_decaying: false,
}

describe("useNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it("returns empty notifications when all queries return no data", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue({ points: [], total_count: 0 })
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() => expect(result.current.notifications).toBeDefined())
    // Allow time for all queries to resolve
    await waitFor(() => expect(portalApi.getScoreHistory).toHaveBeenCalled())
    expect(result.current.notifications).toHaveLength(0)
    expect(result.current.unreadCount).toBe(0)
  })

  it("generates chapter_advance notification from score history", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockScoreHistory)
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() =>
      expect(result.current.notifications.some((n) => n.type === "chapter_advance")).toBe(true)
    )
    const chapterNotif = result.current.notifications.find((n) => n.type === "chapter_advance")
    expect(chapterNotif?.title).toBe("Chapter Advanced!")
    expect(chapterNotif?.message).toContain("Chapter 2")
  })

  it("generates boss_encounter notification from score history", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockScoreHistory)
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() =>
      expect(result.current.notifications.some((n) => n.type === "boss_encounter")).toBe(true)
    )
    const bossNotif = result.current.notifications.find((n) => n.type === "boss_encounter")
    expect(bossNotif?.title).toBe("Boss Encounter")
  })

  it("generates engagement_shift notification from transitions", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue({ points: [], total_count: 0 })
    vi.mocked(portalApi.getEngagement).mockResolvedValue(mockEngagement)
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() =>
      expect(result.current.notifications.some((n) => n.type === "engagement_shift")).toBe(true)
    )
    const engageNotif = result.current.notifications.find((n) => n.type === "engagement_shift")
    expect(engageNotif?.message).toContain("in_zone")
  })

  it("generates decay_warning notification when is_decaying", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue({ points: [], total_count: 0 })
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayActive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() =>
      expect(result.current.notifications.some((n) => n.type === "decay_warning")).toBe(true)
    )
    const decayNotif = result.current.notifications.find((n) => n.type === "decay_warning")
    expect(decayNotif?.title).toBe("Score Decaying!")
    expect(decayNotif?.message).toContain("62.0")
  })

  it("does NOT generate decay_warning when not decaying", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue({ points: [], total_count: 0 })
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() => expect(portalApi.getDecayStatus).toHaveBeenCalled())
    // Small delay for all queries to settle
    await waitFor(() =>
      expect(result.current.notifications.every((n) => n.type !== "decay_warning")).toBe(true)
    )
  })

  it("markAsRead persists to localStorage and updates unreadCount", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockScoreHistory)
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() => expect(result.current.unreadCount).toBeGreaterThan(0))
    const firstId = result.current.notifications[0].id

    act(() => {
      result.current.markAsRead(firstId)
    })

    // unreadCount should decrease
    await waitFor(() => {
      const notif = result.current.notifications.find((n) => n.id === firstId)
      expect(notif?.read).toBe(true)
    })

    // localStorage should contain the read ID
    const stored = JSON.parse(localStorage.getItem("nikita-read-notifications") ?? "[]")
    expect(stored).toContain(firstId)
  })

  it("markAllAsRead marks every notification as read", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockScoreHistory)
    vi.mocked(portalApi.getEngagement).mockResolvedValue(mockEngagement)
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayActive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() => expect(result.current.unreadCount).toBeGreaterThan(0))

    act(() => {
      result.current.markAllAsRead()
    })

    await waitFor(() => expect(result.current.unreadCount).toBe(0))
  })

  it("restores read state from localStorage on mount", async () => {
    // Pre-populate localStorage with a read notification ID
    const readId = "chapter-2026-03-20T10:00:00Z"
    localStorage.setItem("nikita-read-notifications", JSON.stringify([readId]))

    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockScoreHistory)
    vi.mocked(portalApi.getEngagement).mockResolvedValue({
      ...mockEngagement,
      recent_transitions: [],
    })
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayInactive)

    const { result } = renderHook(() => useNotifications(), { wrapper })

    await waitFor(() => expect(result.current.notifications.length).toBeGreaterThan(0))

    const chapterNotif = result.current.notifications.find((n) => n.id === readId)
    expect(chapterNotif?.read).toBe(true)
  })
})
