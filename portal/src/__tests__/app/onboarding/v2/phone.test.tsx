/**
 * Spec 218 Slice 218-8 cleanup — phone-demo modal wiring tests.
 *
 * Verifies PhoneShape respects demo_call_after_submit flag:
 *   - false: onSubmit fires immediately after valid phone
 *   - true:  PhoneDemoModal mounts after valid phone; onSubmit deferred
 *             Skip path: modal skip → onSubmit fires
 *             Consent path: modal consent → PhoneDemoTakeover mounts
 *             Takeover complete → onSubmit fires
 *
 * AC coverage:
 *   AC-P1: demo_call_after_submit=false → onSubmit immediately
 *   AC-P2: demo_call_after_submit=true → modal appears; onSubmit not yet called
 *   AC-P3: modal skip → onSubmit fires with phone value
 *   AC-P4: modal consent → takeover mounts; onSubmit deferred
 *   AC-P5: takeover onComplete → onSubmit fires, takeover unmounts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react"

// --------------------------------------------------------------------------
// Supabase client mock — session with user.id
// --------------------------------------------------------------------------
const mockGetSession = vi.fn().mockResolvedValue({
  data: {
    session: {
      access_token: "test-jwt",
      user: { id: "user-abc-123" },
    },
  },
  error: null,
})

// Realtime channel mock (PhoneDemoTakeover uses it)
let capturedRealtimeCallback: ((payload: { new: { status: string } }) => void) | null = null
const mockSubscribe = vi.fn()
const mockOn = vi.fn().mockImplementation(
  (_event: string, _filter: unknown, cb: (payload: { new: { status: string } }) => void) => {
    capturedRealtimeCallback = cb
    return { subscribe: mockSubscribe }
  },
)
const mockChannel = vi.fn().mockReturnValue({ on: mockOn })
const mockRemoveChannel = vi.fn().mockResolvedValue(undefined)

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession: mockGetSession },
    channel: mockChannel,
    removeChannel: mockRemoveChannel,
  }),
}))

// --------------------------------------------------------------------------
// fetch mock — consent POST returns queued status
// --------------------------------------------------------------------------
const fetchMock = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ status: "queued", provider_call_id: "pc_test_123", message: "Call dispatched" }),
})
vi.stubGlobal("fetch", fetchMock)

import { PhoneShape } from "@/app/onboarding/v2/phone"
import type { PhoneAsk } from "@/app/onboarding/v2/types/envelope"

const VALID_PHONE = "+14155550100"

function makeEnvelope(demoCall: boolean): PhoneAsk {
  return {
    component: "phone",
    handler: "v2",
    slot: "phone",
    prompt: "What's your number?",
    demo_call_after_submit: demoCall,
  }
}

describe("PhoneShape — phone-demo modal wiring", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    capturedRealtimeCallback = null
    mockGetSession.mockClear()
    mockChannel.mockClear()
    mockOn.mockClear()
    mockSubscribe.mockClear()
    mockRemoveChannel.mockClear()
    fetchMock.mockClear()
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ status: "queued", provider_call_id: "pc_test_123", message: "Call dispatched" }),
    })
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it("AC-P1: demo_call_after_submit=false — onSubmit fires immediately after valid phone", () => {
    const onSubmit = vi.fn()
    render(<PhoneShape envelope={makeEnvelope(false)} onSubmit={onSubmit} />)

    const input = screen.getByTestId("v2-phone-input") as HTMLInputElement
    fireEvent.change(input, { target: { value: VALID_PHONE } })
    fireEvent.submit(screen.getByTestId("v2-phone-shape"))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith(VALID_PHONE)
    // No modal should appear
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
  })

  it("AC-P2: demo_call_after_submit=true — modal appears after submit; onSubmit NOT yet called", async () => {
    const onSubmit = vi.fn()
    render(<PhoneShape envelope={makeEnvelope(true)} onSubmit={onSubmit} />)

    const input = screen.getByTestId("v2-phone-input") as HTMLInputElement
    fireEvent.change(input, { target: { value: VALID_PHONE } })
    fireEvent.submit(screen.getByTestId("v2-phone-shape"))

    // Modal should appear
    await waitFor(() => expect(screen.getByRole("alertdialog")).toBeInTheDocument())
    // onSubmit must NOT have fired yet
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("AC-P3: modal skip → onSubmit fires with phone value, modal closes", async () => {
    const onSubmit = vi.fn()
    render(<PhoneShape envelope={makeEnvelope(true)} onSubmit={onSubmit} />)

    const input = screen.getByTestId("v2-phone-input") as HTMLInputElement
    fireEvent.change(input, { target: { value: VALID_PHONE } })
    fireEvent.submit(screen.getByTestId("v2-phone-shape"))

    // Wait for modal
    await waitFor(() => expect(screen.getByRole("alertdialog")).toBeInTheDocument())

    // Click Skip
    fireEvent.click(screen.getByRole("button", { name: /skip/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith(VALID_PHONE)
  })

  it("AC-P4: modal consent → PhoneDemoTakeover mounts; onSubmit NOT yet called", async () => {
    const onSubmit = vi.fn()
    render(<PhoneShape envelope={makeEnvelope(true)} onSubmit={onSubmit} />)

    const input = screen.getByTestId("v2-phone-input") as HTMLInputElement
    fireEvent.change(input, { target: { value: VALID_PHONE } })
    fireEvent.submit(screen.getByTestId("v2-phone-shape"))

    // Wait for modal
    await waitFor(() => expect(screen.getByRole("alertdialog")).toBeInTheDocument())

    // Click "Yes, call me"
    fireEvent.click(screen.getByRole("button", { name: /yes.*call/i }))

    // Consent POST should fire
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/onboarding/phone-demo/consent"),
      expect.objectContaining({ method: "POST" }),
    ))

    // Takeover should mount with aria-live text
    await waitFor(() =>
      expect(screen.getByText(/nikita is calling\. please wait\./i)).toBeInTheDocument(),
    )

    // onSubmit must NOT have fired yet
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("AC-P5: takeover onComplete → onSubmit fires, takeover unmounts", async () => {
    const onSubmit = vi.fn()
    render(<PhoneShape envelope={makeEnvelope(true)} onSubmit={onSubmit} />)

    const input = screen.getByTestId("v2-phone-input") as HTMLInputElement
    fireEvent.change(input, { target: { value: VALID_PHONE } })
    fireEvent.submit(screen.getByTestId("v2-phone-shape"))

    await waitFor(() => expect(screen.getByRole("alertdialog")).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: /yes.*call/i }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())

    // Wait for takeover to mount
    await waitFor(() =>
      expect(screen.getByText(/nikita is calling\. please wait\./i)).toBeInTheDocument(),
    )

    // Trigger takeover completion via Realtime event
    act(() => {
      capturedRealtimeCallback?.({ new: { status: "ended_success" } })
    })

    // onSubmit fires after takeover completes
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith(VALID_PHONE)

    // Takeover unmounts
    expect(screen.queryByText(/nikita is calling\. please wait\./i)).not.toBeInTheDocument()
  })
})
