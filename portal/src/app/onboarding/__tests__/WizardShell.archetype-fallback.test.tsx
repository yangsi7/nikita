/**
 * Spec 217-2 FR-4a — ArchetypeFallback component tests.
 *
 * ACs verified:
 *   - AC-T.1   (a) Alert renders when `archetype_cards === null` after the
 *              fallback timeout; (b) retry click invokes the supplied
 *              `onRetry` callback (which the parent wires to a fresh
 *              `submitAnswer` POST using the cached turn_id idempotency).
 *   - AC-T.1bis virtualized clock via `vi.useFakeTimers()` +
 *              `vi.advanceTimersByTime(...)`. NEVER real wall-clock —
 *              would slow CI by 4 s per re-run.
 *
 * The fallback is exported from WizardShell so it can be unit-tested in
 * isolation. The integration path (FE guard + retry threading) is
 * covered by the manual Walk B2 protocol per AC-W.1+2; pre-merge tests
 * stay at the component level for speed and determinism.
 */

import { render, screen, fireEvent, act } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ArchetypeFallback } from "../_components/ArchetypeFallback"

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe("ArchetypeFallback — Spec 217-2 FR-4a", () => {
  it("does not render the Alert before the fallback timeout elapses", () => {
    render(<ArchetypeFallback onRetry={vi.fn()} timeoutMs={4000} />)
    // Pre-timeout: only the placeholder line is visible — no alert role.
    expect(screen.queryByRole("alert")).toBeNull()
    expect(screen.getByText(/preparing the three of us/i)).toBeInTheDocument()
  })

  it("renders an Alert with a retry button after the timeout (AC-T.1.a, AC-T.1bis)", () => {
    render(<ArchetypeFallback onRetry={vi.fn()} timeoutMs={4000} />)
    expect(screen.queryByRole("alert")).toBeNull()
    act(() => {
      vi.advanceTimersByTime(4000)
    })
    const alert = screen.getByRole("alert")
    expect(alert).toBeInTheDocument()
    // Retry CTA — labelled accessibly so screen readers find it.
    expect(
      screen.getByRole("button", { name: /try again/i })
    ).toBeInTheDocument()
  })

  it("invokes onRetry when the retry button is clicked (AC-T.1.b)", () => {
    const onRetry = vi.fn()
    render(<ArchetypeFallback onRetry={onRetry} timeoutMs={4000} />)
    act(() => {
      vi.advanceTimersByTime(4000)
    })
    fireEvent.click(screen.getByRole("button", { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it("emits a structured warn log when the fallback fires (AC-4a.4)", () => {
    const warnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => undefined)
    try {
      render(<ArchetypeFallback onRetry={vi.fn()} timeoutMs={4000} />)
      act(() => {
        vi.advanceTimersByTime(4000)
      })
      // Console.warn is called with a stable event name + structured payload
      // (per AC-4a.4: `backstory_fallback_fired`, `reason: "null_cards"`).
      expect(warnSpy).toHaveBeenCalledWith(
        "backstory_fallback_fired",
        expect.objectContaining({ reason: "null_cards" })
      )
    } finally {
      warnSpy.mockRestore()
    }
  })

  it("clears the timer on unmount so a stale Alert never shows post-cleanup", () => {
    const { unmount } = render(
      <ArchetypeFallback onRetry={vi.fn()} timeoutMs={4000} />
    )
    unmount()
    // Advancing past the deadline after unmount must NOT crash (no setState
    // on unmounted component) — guarded by useEffect cleanup.
    act(() => {
      vi.advanceTimersByTime(10_000)
    })
    expect(screen.queryByRole("alert")).toBeNull()
  })
})
