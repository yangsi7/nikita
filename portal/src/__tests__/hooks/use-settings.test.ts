/**
 * Tests for useSettings hook (query + mutations)
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { UserSettings } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    linkTelegram: vi.fn(),
    deleteAccount: vi.fn(),
  },
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { toast } from "sonner"
import { useSettings } from "@/hooks/use-settings"

function createWrapper() {
  const qc = createTestQueryClient()
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
  return { wrapper, qc }
}

const mockSettings: UserSettings = {
  email: "player@example.com",
  timezone: "Europe/Zurich",
  telegram_linked: true,
  telegram_username: "player123",
  notifications_enabled: true,
}

describe("useSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches settings on mount", async () => {
    vi.mocked(portalApi.getSettings).mockResolvedValue(mockSettings)
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useSettings(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockSettings)
    expect(result.current.data?.email).toBe("player@example.com")
  })

  it("uses correct query key ['portal', 'settings']", async () => {
    vi.mocked(portalApi.getSettings).mockResolvedValue(mockSettings)
    const { wrapper, qc } = createWrapper()

    const { result } = renderHook(() => useSettings(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "settings"])
    expect(cached).toEqual(mockSettings)
  })

  it("updateSettings calls API and shows success toast", async () => {
    vi.mocked(portalApi.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(portalApi.updateSettings).mockResolvedValue({
      ...mockSettings,
      timezone: "America/New_York",
    })
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useSettings(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    act(() => {
      result.current.updateSettings({ timezone: "America/New_York" })
    })

    await waitFor(() => expect(portalApi.updateSettings).toHaveBeenCalled())
    expect(portalApi.updateSettings).toHaveBeenCalledWith({ timezone: "America/New_York" })
    expect(toast.success).toHaveBeenCalledWith("Settings saved")
  })

  it("shows error toast when updateSettings fails", async () => {
    vi.mocked(portalApi.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(portalApi.updateSettings).mockRejectedValue(new Error("fail"))
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useSettings(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    act(() => {
      result.current.updateSettings({ timezone: "bad" })
    })

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Failed to save settings"))
  })

  it("linkTelegram calls API and shows success toast", async () => {
    vi.mocked(portalApi.getSettings).mockResolvedValue(mockSettings)
    vi.mocked(portalApi.linkTelegram).mockResolvedValue({ code: "ABC123" })
    const { wrapper } = createWrapper()

    const { result } = renderHook(() => useSettings(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    await act(async () => {
      await result.current.linkTelegram()
    })

    expect(portalApi.linkTelegram).toHaveBeenCalled()
    expect(toast.success).toHaveBeenCalledWith("Telegram link code generated")
  })
})
