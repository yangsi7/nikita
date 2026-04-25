import { createElement } from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, act } from "@testing-library/react"

// Override the global framer-motion mock so useReducedMotion is available.
// The global mock in `vitest.setup.ts` only covers `motion.*` element access.
vi.mock("framer-motion", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, react/display-name
  const mc = (tag: string) => ({ children, ...p }: any) => createElement(tag, p, children)
  const motion = new Proxy({}, { get: (_: object, t: string) => mc(t) })
  return {
    motion,
    useInView: () => true,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
    useReducedMotion: () => reducedMotionMock(),
  }
})

// Mutable toggle for the mocked hook. Default: no reduced motion.
let reducedMotionMock: () => boolean = () => false

import { DossierStamp } from "@/app/onboarding/components/DossierStamp"

// Spec 214 PR 214-B — T210 (RED)
// Tests:
//   - CLEARED: typewriter reveal (characters appear progressively)
//   - ANALYZED: stamp-rotate animation (framer-motion rotate prop path)
//   - prefers-reduced-motion: skip animation, show final state immediately
// References spec §Appendix C + `docs/content/wizard-copy.md` DossierStamp
// states table.

describe("DossierStamp — CLEARED state (typewriter reveal)", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("reveals CLEARED character-by-character with a 40ms tick", () => {
    render(<DossierStamp state="cleared" />)
    // At t=0 no characters have been revealed yet (the full text is not present)
    expect(screen.queryByText("CLEARED")).not.toBeInTheDocument()

    // After 40ms * 7 chars = 280ms the full stamp renders
    act(() => {
      vi.advanceTimersByTime(40 * 7 + 10)
    })
    expect(screen.getByText("CLEARED")).toBeInTheDocument()
  })

  it("applies the primary-rose dossier-stamp class for CLEARED", () => {
    render(<DossierStamp state="cleared" />)
    act(() => {
      vi.advanceTimersByTime(40 * 7 + 10)
    })
    const el = screen.getByText("CLEARED")
    expect(el.className).toContain("text-primary")
    expect(el.className).toContain("tracking-widest")
    expect(el.className).toContain("uppercase")
  })
})

describe("DossierStamp — ANALYZED state (stamp-rotate)", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
  })

  it("renders the ANALYZED stamp with a rotate animation config", () => {
    render(<DossierStamp state="analyzed" />)
    expect(screen.getByText("ANALYZED")).toBeInTheDocument()
    // Rotation is driven through framer-motion's animate prop. The proxied
    // mock renders motion.span as span; the `animate` prop ends up as an
    // attribute value on the DOM node (stringified object). Assert it
    // mentions the rotate sequence described in §Appendix C.
    const el = screen.getByText("ANALYZED")
    // The proxied motion mock forwards props as plain DOM attrs; scan the
    // serialized attrs for a rotate signature.
    expect(el.outerHTML).toMatch(/rotate/i)
  })
})

describe("DossierStamp — prefers-reduced-motion (a11y)", () => {
  beforeEach(() => {
    reducedMotionMock = () => true
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("skips the typewriter and shows CLEARED immediately under reduced motion", () => {
    render(<DossierStamp state="cleared" />)
    // No timer advance — stamp must be present on first paint
    expect(screen.getByText("CLEARED")).toBeInTheDocument()
  })

  it("skips the stamp-rotate animation under reduced motion for ANALYZED", () => {
    render(<DossierStamp state="analyzed" />)
    const el = screen.getByText("ANALYZED")
    // Under reduced motion the component should NOT emit a rotate animation
    // config. Assert the serialized attrs do not contain rotate.
    expect(el.outerHTML).not.toMatch(/rotate/i)
  })
})

describe("DossierStamp — other states", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
  })

  it("renders the pending stamp with muted opacity + pulse", () => {
    render(<DossierStamp state="clearance-pending" />)
    const el = screen.getByText("SETTING UP...")
    expect(el.className).toContain("animate-pulse")
  })

  it("renders the PROVISIONAL — READY stamp without any animation", () => {
    render(<DossierStamp state="provisional" />)
    expect(screen.getByText("PROVISIONAL — READY")).toBeInTheDocument()
  })

  it("renders the CONFIRMED stamp immediately (no timer)", () => {
    render(<DossierStamp state="confirmed" />)
    expect(screen.getByText("CONFIRMED")).toBeInTheDocument()
  })

  it("renders the ANALYSIS: PENDING stamp for backstory-degraded path", () => {
    render(<DossierStamp state="analysis-pending" />)
    expect(screen.getByText("ANALYSIS: PENDING")).toBeInTheDocument()
  })
})
