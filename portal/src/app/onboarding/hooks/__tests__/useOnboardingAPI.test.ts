import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Mock the apiClient transport — the hook should delegate to it for every
// method (post/put/patch). The hook layer only owns the retry policy and
// the typed wrappers around onboarding-specific paths.
vi.mock("@/lib/api/client", () => {
  return {
    api: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  }
})

import { renderHook } from "@testing-library/react"

import { useOnboardingAPI, withRetry } from "@/app/onboarding/hooks/use-onboarding-api"
import { api } from "@/lib/api/client"

// Spec 214 PR 214-A — T102 (RED)
// Tests AC-4.2 (PUT idempotency wrapper), AC-6.2 (PATCH always carries
// wizard_step from caller), AC-10.1 (PUT body shape).

const mocked = api as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  patch: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

describe("withRetry — exponential backoff (NFR-001)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("returns the resolved value on first success without scheduling retries", async () => {
    const op = vi.fn().mockResolvedValueOnce("ok")
    const promise = withRetry(op, { method: "GET" })
    await expect(promise).resolves.toBe("ok")
    expect(op).toHaveBeenCalledTimes(1)
  })

  it("retries up to 3 times for retryable methods with 500/1000/2000ms delays", async () => {
    const op = vi
      .fn()
      .mockRejectedValueOnce(new Error("net1"))
      .mockRejectedValueOnce(new Error("net2"))
      .mockResolvedValueOnce("ok")

    const promise = withRetry(op, { method: "GET" })
    // Drain microtasks so the first rejection schedules the first delay
    await vi.advanceTimersByTimeAsync(0)
    expect(op).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(500)
    expect(op).toHaveBeenCalledTimes(2)

    await vi.advanceTimersByTimeAsync(1000)
    expect(op).toHaveBeenCalledTimes(3)

    await expect(promise).resolves.toBe("ok")
  })

  it("gives up and throws after 3 attempts on persistent failure", async () => {
    const err = new Error("persistent")
    const op = vi.fn().mockRejectedValue(err)

    const promise = withRetry(op, { method: "GET" })
    // Suppress unhandled rejection while we advance the timer schedule
    promise.catch(() => undefined)

    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(500)
    await vi.advanceTimersByTimeAsync(1000)
    await vi.advanceTimersByTimeAsync(2000)

    await expect(promise).rejects.toBe(err)
    expect(op).toHaveBeenCalledTimes(3)
  })

  it("does NOT retry POST (non-idempotent)", async () => {
    const err = new Error("server")
    const op = vi.fn().mockRejectedValue(err)
    const promise = withRetry(op, { method: "POST" })
    promise.catch(() => undefined)
    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(2000)
    await expect(promise).rejects.toBe(err)
    expect(op).toHaveBeenCalledTimes(1)
  })
})

describe("useOnboardingAPI — wrappers (spec FR-4, FR-6, FR-7, FR-9)", () => {
  beforeEach(() => {
    vi.useRealTimers()
    mocked.get.mockReset()
    mocked.post.mockReset()
    mocked.put.mockReset()
    mocked.patch.mockReset()
  })

  it("previewBackstory POSTs to /onboarding/preview-backstory with the request body", async () => {
    mocked.post.mockResolvedValueOnce({
      scenarios: [],
      venues_used: [],
      cache_key: "k1",
      degraded: true,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.previewBackstory({
      city: "Berlin",
      social_scene: "techno",
      darkness_level: 3,
      life_stage: null,
      interest: null,
      age: null,
      occupation: null,
    })
    expect(mocked.post).toHaveBeenCalledWith(
      "/onboarding/preview-backstory",
      expect.objectContaining({ city: "Berlin", darkness_level: 3 })
    )
  })

  it("submitProfile POSTs to /onboarding/profile (FR-7, AC-7.1)", async () => {
    mocked.post.mockResolvedValueOnce({
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.submitProfile({
      location_city: "Berlin",
      social_scene: "techno",
      drug_tolerance: 4,
      wizard_step: 10,
    })
    expect(mocked.post).toHaveBeenCalledWith(
      "/onboarding/profile",
      expect.objectContaining({ wizard_step: 10 })
    )
  })

  it("patchProfile PATCHes /onboarding/profile and always carries wizard_step (AC-6.2)", async () => {
    mocked.patch.mockResolvedValueOnce({
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.patchProfile({
      location_city: "Berlin",
      wizard_step: 4,
    })
    expect(mocked.patch).toHaveBeenCalledWith(
      "/onboarding/profile",
      expect.objectContaining({ wizard_step: 4, location_city: "Berlin" })
    )
  })

  it("selectBackstory PUTs the BackstoryChoiceRequest body to /onboarding/profile/chosen-option (AC-10.1)", async () => {
    mocked.put.mockResolvedValueOnce({
      user_id: "u",
      pipeline_state: "ready",
      backstory_options: [],
      chosen_option: {
        id: "abc123def456",
        venue: "Goldman",
        context: "ctx",
        the_moment: "moment",
        unresolved_hook: "hook",
        tone: "romantic",
      },
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.selectBackstory("abc123def456", "v1:berlin:techno:4:tech:0:0:designer")
    expect(mocked.put).toHaveBeenCalledWith(
      "/onboarding/profile/chosen-option",
      {
        chosen_option_id: "abc123def456",
        cache_key: "v1:berlin:techno:4:tech:0:0:designer",
      }
    )
  })

  it("selectBackstory is idempotent — returns the response without retrying on success (AC-9.2)", async () => {
    mocked.put.mockResolvedValueOnce({
      user_id: "u",
      pipeline_state: "ready",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    const { result } = renderHook(() => useOnboardingAPI())
    await result.current.selectBackstory("id1", "key1")
    expect(mocked.put).toHaveBeenCalledTimes(1)
  })
})

// Spec 214 AC-11b.1 / GH #321 REQ-2 — linkTelegram hook method
describe("useOnboardingAPI — linkTelegram (GH #321 REQ-2)", () => {
  beforeEach(() => {
    // Clear call history on the module-level `api.post` spy so sibling-test
    // call counts don't leak between `it(...)` blocks. `restoreAllMocks` is
    // insufficient because api.* are vi.fn()s defined via the vi.mock factory
    // at the top of this file (not spies).
    mocked.post.mockClear()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("linkTelegram calls POST /portal/link-telegram with no body", async () => {
    mocked.post.mockResolvedValueOnce({
      code: "ABC123",
      expires_at: "2026-04-17T20:00:00Z",
      instructions: "Send /link ABC123 to @Nikita_my_bot on Telegram.",
    })
    const { result } = renderHook(() => useOnboardingAPI())
    const response = await result.current.linkTelegram()

    expect(mocked.post).toHaveBeenCalledTimes(1)
    expect(mocked.post).toHaveBeenCalledWith("/portal/link-telegram")
    expect(response.code).toBe("ABC123")
    expect(response.expires_at).toBe("2026-04-17T20:00:00Z")
  })

  it("linkTelegram does NOT retry on failure (non-idempotent POST)", async () => {
    const err = new Error("server 500")
    mocked.post.mockRejectedValueOnce(err)

    const { result } = renderHook(() => useOnboardingAPI())

    await expect(result.current.linkTelegram()).rejects.toThrow("server 500")
    expect(mocked.post).toHaveBeenCalledTimes(1)
  })
})
