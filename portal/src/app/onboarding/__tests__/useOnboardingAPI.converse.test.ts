/**
 * Spec 214 T3.4 — useOnboardingAPI.converse() idempotency header + no-retry.
 *
 * ACs:
 *   - AC-T3.4.1: turn_id is a UUID; Idempotency-Key header matches body turn_id
 *   - AC-T3.4.2: 429 handled by caller (we just verify error surface carries status)
 *
 * Pattern: mock `@/lib/api/client` to capture call args, then invoke the
 * hook from a `renderHook` + synchronously call converse.
 */

import { renderHook } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/lib/api/client", () => {
  const post = vi.fn()
  return {
    api: {
      get: vi.fn(),
      post,
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  }
})

import { api } from "@/lib/api/client"
import { useOnboardingAPI } from "../hooks/use-onboarding-api"

describe("useOnboardingAPI.converse — T3.4 idempotency + wire shape", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("AC-T3.4.1: generates UUID turn_id, Idempotency-Key header matches body", async () => {
    ;(api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      nikita_reply: "hi",
      extracted_fields: {},
      confirmation_required: false,
      next_prompt_type: "text",
      progress_pct: 10,
      conversation_complete: false,
      source: "llm",
      latency_ms: 100,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.converse({
      conversation_history: [],
      user_input: "zurich",
    })
    expect(api.post).toHaveBeenCalledTimes(1)
    const [path, body, headers] = (api.post as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(path).toBe("/onboarding/converse")
    const bodyObj = body as { turn_id?: string; user_input: unknown }
    expect(typeof bodyObj.turn_id).toBe("string")
    // UUID v4 shape (36 chars, hyphenated)
    expect(bodyObj.turn_id).toMatch(/^[0-9a-f-]{36}$/i)
    const headerObj = headers as { "Idempotency-Key": string }
    expect(headerObj["Idempotency-Key"]).toBe(bodyObj.turn_id)
  })

  it("normalizes text-kind ControlSelection to raw string in body", async () => {
    ;(api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      nikita_reply: "ok",
      extracted_fields: {},
      confirmation_required: false,
      next_prompt_type: "text",
      progress_pct: 0,
      conversation_complete: false,
      source: "llm",
      latency_ms: 1,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.converse({
      conversation_history: [],
      user_input: { kind: "text", value: "berlin" },
    })
    const [, body] = (api.post as ReturnType<typeof vi.fn>).mock.calls[0]
    const bodyObj = body as { user_input: unknown }
    expect(bodyObj.user_input).toBe("berlin")
  })

  it("chip payload survives as discriminated union in body", async () => {
    ;(api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      nikita_reply: "ok",
      extracted_fields: {},
      confirmation_required: false,
      next_prompt_type: "text",
      progress_pct: 0,
      conversation_complete: false,
      source: "llm",
      latency_ms: 1,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.converse({
      conversation_history: [],
      user_input: { kind: "chips", value: "techno" },
    })
    const [, body] = (api.post as ReturnType<typeof vi.fn>).mock.calls[0]
    const bodyObj = body as { user_input: unknown }
    expect(bodyObj.user_input).toEqual({ kind: "chips", value: "techno" })
  })

  it("AC-T3.4.2: 429 rejection surfaces status so caller can render in-character bubble", async () => {
    ;(api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({
      status: 429,
      detail: "easy, tiger. give me a sec.",
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await expect(
      result.current.converse({
        conversation_history: [],
        user_input: "zurich",
      })
    ).rejects.toMatchObject({ status: 429 })
    // Assert NO retry wrapper: only one network call.
    expect(api.post).toHaveBeenCalledTimes(1)
  })
})
