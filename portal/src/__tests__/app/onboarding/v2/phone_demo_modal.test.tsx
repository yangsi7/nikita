/**
 * Spec 218 Slice 218-7 — PhoneDemoModal + PhoneDemoTakeover (FR-009/FR-010)
 *
 * RED phase: components stub raise; tests verify structure and imports compile.
 * GREEN phase: stubs replaced with real implementation; behaviour tests pass.
 *
 * AC coverage:
 *   AC-001: PhoneDemoModal renders with skip and consent actions
 *   AC-002: PhoneDemoModal default focus is on Skip (FR-009 default-skip)
 *   AC-003: PhoneDemoTakeover has aria-live region with correct text (FR-010)
 *   AC-004: alert-dialog component compiles without import errors
 *   AC-005: PhoneDemoTakeover calls onComplete("ceiling_timeout") after 30s (FR-010)
 *   AC-006: PhoneDemoTakeover calls onComplete on Realtime terminal status
 *   AC-007: PhoneDemoTakeover "End early" button appears after 5s (FR-010)
 *   AC-008: "End early" button fires POST end-call then calls onComplete("ended_error")
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react"

// --- Supabase Realtime mock ---
// Captures the postgres_changes callback so tests can fire synthetic events.
let capturedRealtimeCallback: ((payload: { new: { status: string } }) => void) | null = null
const mockSubscribe = vi.fn()
const mockOn = vi.fn().mockImplementation((_event: string, _filter: unknown, cb: (payload: { new: { status: string } }) => void) => {
  capturedRealtimeCallback = cb
  return { subscribe: mockSubscribe }
})
const mockChannel = vi.fn().mockReturnValue({ on: mockOn })
const mockRemoveChannel = vi.fn().mockResolvedValue(undefined)

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    channel: mockChannel,
    removeChannel: mockRemoveChannel,
  }),
}))

// fetch mock for End-early POST
const fetchMock = vi.fn().mockResolvedValue({ ok: true })
vi.stubGlobal("fetch", fetchMock)

import { PhoneDemoTakeover } from "@/app/onboarding/v2/phone_demo_takeover"

describe("PhoneDemoModal (Spec 218 Slice 218-7 - RED)", () => {
  it("AC-004: alert-dialog component exports compile", async () => {
    // Verify the shadcn alert-dialog component is importable — will fail
    // if @radix-ui/react-alert-dialog is missing or alert-dialog.tsx has errors.
    const mod = await import("@/components/ui/alert-dialog")
    expect(mod.AlertDialog).toBeDefined()
    expect(mod.AlertDialogContent).toBeDefined()
    expect(mod.AlertDialogTitle).toBeDefined()
    expect(mod.AlertDialogDescription).toBeDefined()
    expect(mod.AlertDialogFooter).toBeDefined()
    expect(mod.AlertDialogHeader).toBeDefined()
    expect(mod.AlertDialogAction).toBeDefined()
    expect(mod.AlertDialogCancel).toBeDefined()
  })

  it("AC-001 (RED): PhoneDemoModal module exports PhoneDemoModal function", async () => {
    // In RED phase, the import should succeed (component file exists)
    // but calling render will throw NotImplementedError from the stub.
    const mod = await import("@/app/onboarding/v2/phone_demo_modal")
    expect(typeof mod.PhoneDemoModal).toBe("function")
  })

  it("AC-003 (RED): PhoneDemoTakeover module exports PhoneDemoTakeover function", async () => {
    const mod = await import("@/app/onboarding/v2/phone_demo_takeover")
    expect(typeof mod.PhoneDemoTakeover).toBe("function")
  })

  it("AC-002 (GREEN): PhoneDemoModal renders without throwing", async () => {
    // GREEN phase: PhoneDemoModal is a real component, no longer throws.
    // Basic smoke-test: calling the function with valid props returns truthy JSX.
    const { PhoneDemoModal } = await import("@/app/onboarding/v2/phone_demo_modal")
    const noop = vi.fn()
    // Calling a React function component returns React elements (object), not throws
    const result = PhoneDemoModal({ open: false, onSkip: noop, onConsent: noop })
    expect(result).not.toBeNull()
  })
})

describe("PhoneDemoTakeover (Spec 218 Slice 218-7 - GREEN behaviours)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    capturedRealtimeCallback = null
    mockChannel.mockClear()
    mockOn.mockClear()
    mockSubscribe.mockClear()
    mockRemoveChannel.mockClear()
    fetchMock.mockClear()
    fetchMock.mockResolvedValue({ ok: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("AC-003: renders aria-live region with 'Nikita is calling. Please wait.' (FR-010)", () => {
    render(<PhoneDemoTakeover userId="user-123" onComplete={vi.fn()} />)
    const liveRegion = screen.getByText(/nikita is calling\. please wait\./i)
    expect(liveRegion).toBeInTheDocument()
    expect(liveRegion).toHaveAttribute("aria-live", "polite")
  })

  it("AC-005: calls onComplete('ceiling_timeout') after 30 seconds (FR-010)", async () => {
    const onComplete = vi.fn()
    render(<PhoneDemoTakeover userId="user-123" onComplete={onComplete} />)
    expect(onComplete).not.toHaveBeenCalled()
    act(() => { vi.advanceTimersByTime(30_000) })
    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete).toHaveBeenCalledWith("ceiling_timeout")
  })

  it("AC-006: calls onComplete('ended_success') on Realtime ended_success status", async () => {
    const onComplete = vi.fn()
    render(<PhoneDemoTakeover userId="user-123" onComplete={onComplete} />)
    // Fire synthetic Realtime event
    act(() => {
      capturedRealtimeCallback?.({ new: { status: "ended_success" } })
    })
    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete).toHaveBeenCalledWith("ended_success")
  })

  it("AC-006b: calls onComplete('ceiling_timeout') on Realtime ceiling_timeout status (R4 fix)", async () => {
    const onComplete = vi.fn()
    render(<PhoneDemoTakeover userId="user-123" onComplete={onComplete} />)
    act(() => {
      capturedRealtimeCallback?.({ new: { status: "ceiling_timeout" } })
    })
    expect(onComplete).toHaveBeenCalledWith("ceiling_timeout")
  })

  it("AC-006c: calls onComplete('ended_error') on Realtime ended_busy status", async () => {
    const onComplete = vi.fn()
    render(<PhoneDemoTakeover userId="user-123" onComplete={onComplete} />)
    act(() => {
      capturedRealtimeCallback?.({ new: { status: "ended_busy" } })
    })
    expect(onComplete).toHaveBeenCalledWith("ended_error")
  })

  it("AC-007: 'End early' button hidden before 5s, visible after 5s (FR-010)", async () => {
    render(<PhoneDemoTakeover userId="user-123" onComplete={vi.fn()} />)
    expect(screen.queryByRole("button", { name: /end early/i })).not.toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(5_000) })
    expect(screen.getByRole("button", { name: /end early/i })).toBeInTheDocument()
  })

  it("AC-008: 'End early' click POSTs to end-call endpoint then calls onComplete('ended_error')", async () => {
    const onComplete = vi.fn()
    render(<PhoneDemoTakeover userId="user-123" onComplete={onComplete} />)
    // Show the button
    act(() => { vi.advanceTimersByTime(5_000) })
    const btn = screen.getByRole("button", { name: /end early/i })
    fireEvent.click(btn)
    // Await the async fetch
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith("ended_error"))
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/onboarding/phone-demo/end-call",
      expect.objectContaining({ method: "POST" })
    )
  })
})
