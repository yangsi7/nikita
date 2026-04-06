/**
 * Tests for GodModePanel component
 * Verifies mutation buttons render and dialog opens on click
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { GodModePanel } from "@/components/admin/god-mode-panel"

// Mock the admin mutations hook
const mockMutations = {
  setScore: { mutate: vi.fn(), isPending: false },
  setChapter: { mutate: vi.fn(), isPending: false },
  setStatus: { mutate: vi.fn(), isPending: false },
  setEngagement: { mutate: vi.fn(), isPending: false },
  resetBoss: { mutate: vi.fn(), isPending: false },
  clearEngagement: { mutate: vi.fn(), isPending: false },
  setMetrics: { mutate: vi.fn(), isPending: false },
  triggerPipeline: { mutate: vi.fn(), isPending: false },
}

vi.mock("@/hooks/use-admin-mutations", () => ({
  useAdminMutations: () => mockMutations,
}))

describe("GodModePanel", () => {
  it("renders God Mode heading", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByText("God Mode")).toBeInTheDocument()
  })

  it("renders Set Score input and button", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByText("Set Score (0-100)")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("0-100")).toBeInTheDocument()
  })

  it("renders Set Chapter controls", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByText("Set Chapter")).toBeInTheDocument()
  })

  it("renders Set Game Status controls", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByText("Set Game Status")).toBeInTheDocument()
  })

  it("renders Set Engagement controls", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByText("Set Engagement")).toBeInTheDocument()
  })

  it("renders action buttons: Reset Boss, Clear Engagement, Trigger Pipeline", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByText("Reset Boss")).toBeInTheDocument()
    expect(screen.getByText("Clear Engagement")).toBeInTheDocument()
    expect(screen.getByText("Trigger Pipeline")).toBeInTheDocument()
  })

  it("renders reason input", () => {
    render(<GodModePanel userId="user-123" />)
    expect(screen.getByPlaceholderText("Why are you doing this?")).toBeInTheDocument()
  })

  it("opens confirmation dialog when Reset Boss is clicked", async () => {
    const user = userEvent.setup()
    render(<GodModePanel userId="user-123" />)

    await user.click(screen.getByText("Reset Boss"))

    // Dialog should appear with title and Confirm button
    expect(screen.getByText("Reset boss encounter?")).toBeInTheDocument()
    expect(screen.getByText("Confirm")).toBeInTheDocument()
    expect(screen.getByText("Cancel")).toBeInTheDocument()
  })
})
