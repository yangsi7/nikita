/**
 * Tests for useIsMobile hook
 * Uses matchMedia to detect mobile breakpoint (< 768px)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useIsMobile } from "@/hooks/use-mobile"

describe("useIsMobile", () => {
  let matchMediaListeners: Array<() => void> = []
  const originalInnerWidth = window.innerWidth

  function mockMatchMedia(matches: boolean) {
    matchMediaListeners = []
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: (_event: string, cb: () => void) => {
          matchMediaListeners.push(cb)
        },
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  }

  beforeEach(() => {
    mockMatchMedia(false)
  })

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", { value: originalInnerWidth, writable: true, configurable: true })
  })

  it("returns false for desktop width (>= 768px)", () => {
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true, configurable: true })
    mockMatchMedia(false)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it("returns true for mobile width (< 768px)", () => {
    Object.defineProperty(window, "innerWidth", { value: 375, writable: true, configurable: true })
    mockMatchMedia(true)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(true)
  })

  it("queries matchMedia with correct breakpoint (767px)", () => {
    renderHook(() => useIsMobile())
    expect(window.matchMedia).toHaveBeenCalledWith("(max-width: 767px)")
  })

  it("updates when window resizes across breakpoint", () => {
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true, configurable: true })
    mockMatchMedia(false)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)

    // Simulate resize to mobile
    act(() => {
      Object.defineProperty(window, "innerWidth", { value: 375, writable: true, configurable: true })
      matchMediaListeners.forEach((cb) => cb())
    })

    expect(result.current).toBe(true)
  })
})
