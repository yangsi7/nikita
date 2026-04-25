import { createElement } from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, act } from "@testing-library/react"

// Override the global framer-motion mock so DossierStamp's
// useReducedMotion path resolves predictably (see DossierStamp.test.tsx
// for the same pattern).
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

let reducedMotionMock: () => boolean = () => false
let innerWidthMock = 1280

import { ClearanceGrantedCeremony } from "@/app/onboarding/components/ClearanceGrantedCeremony"

beforeEach(() => {
  reducedMotionMock = () => false
  innerWidthMock = 1280
  Object.defineProperty(window, "innerWidth", {
    writable: true,
    configurable: true,
    value: innerWidthMock,
  })
  // jsdom has no native matchMedia; mirror QRHandoff's expectation.
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: query.includes("min-width: 768px") ? innerWidthMock >= 768 : false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    onchange: null,
    dispatchEvent: vi.fn(),
  }))
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe("ClearanceGrantedCeremony — Spec 214 T4.1 (FR-11e)", () => {
  it("test_dom_snapshot_and_qr_conditional_render: full viewport with stamp + Nikita line + CTA + QR on desktop", () => {
    render(<ClearanceGrantedCeremony linkCode="ABC123" />)
    // Drain DossierStamp's CLEARED typewriter so the assertion isn't
    // racing against partial text reveal.
    act(() => {
      vi.advanceTimersByTime(40 * 8)
    })

    // Full-viewport container (AC-T4.1.1).
    const root = screen.getByTestId("clearance-granted-ceremony")
    expect(root.className).toContain("min-h-[100dvh]")

    // Stamp surface: you're in + DossierStamp + ready.
    expect(screen.getByText("you're in.")).toBeInTheDocument()
    expect(screen.getByText("CLEARED")).toBeInTheDocument()
    expect(
      screen.getByTestId("ceremony-clearance-granted").textContent
    ).toBe("ready.")

    // Nikita's final line — exact copy match guards against drift +
    // confirms em-dash-free phrasing (the literal string contains no
    // em-dash; pre-PR grep gates also catch this).
    const finalLine = screen.getByTestId("ceremony-nikita-line")
    expect(finalLine.textContent).toBe(
      "got everything i need. see you on Telegram in a second."
    )
    expect(finalLine.textContent).not.toContain("\u2014")

    // CTA → t.me deep-link.
    const cta = screen.getByTestId("ceremony-cta") as HTMLAnchorElement
    expect(cta.textContent).toBe("Meet her on Telegram")
    expect(cta.href).toBe("https://t.me/Nikita_my_bot?start=ABC123")

    // Desktop ≥768px → QR rendered (AC-T4.1.1 conditional half).
    expect(screen.getByTestId("qr-handoff")).toBeInTheDocument()
  })

  it("test_dom_snapshot_and_qr_conditional_render: mobile viewport hides QR", () => {
    innerWidthMock = 320
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: innerWidthMock,
    })
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes("min-width: 768px") ? false : false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    }))

    render(<ClearanceGrantedCeremony linkCode="MOBILE" />)
    expect(screen.queryByTestId("qr-handoff")).not.toBeInTheDocument()
    // CTA still present on mobile (mobile is the PRIMARY platform).
    expect(screen.getByTestId("ceremony-cta")).toBeInTheDocument()
  })

  it("test_reduced_motion_skips_animation: stamp paints final state immediately when reduced motion is enabled", () => {
    reducedMotionMock = () => true
    render(<ClearanceGrantedCeremony linkCode="REDUCE" />)
    // Under reduced motion, DossierStamp short-circuits its
    // typewriter reveal; the final "CLEARED" string MUST be present
    // at t=0 without any timer advance.
    expect(screen.getByText("CLEARED")).toBeInTheDocument()
  })

  it("test_cta_href_requires_pre_minted_code: throws when linkCode is null", () => {
    // Render with a null linkCode is a programming bug — the reducer
    // mints the code BEFORE the ceremony mounts (per the wizard's
    // T3.9.4 contract). Throwing fails loud; silently rendering a
    // CTA pointing at `?start=` would land the user on Telegram
    // without a binding token (silent strand).
    //
    // React surfaces render-thrown errors via an error boundary;
    // without one, RTL re-throws synchronously which is what we
    // assert here. Suppress the noisy console.error React emits
    // for unhandled render errors during this expectation.
    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => {})
    expect(() =>
      render(<ClearanceGrantedCeremony linkCode={null} />)
    ).toThrow(/linkCode/)
    consoleErrorSpy.mockRestore()
  })

  it("test_cta_href_url_encodes_link_code: special chars in code are encoded", () => {
    // Defensive: even though codes are `^[A-Z0-9]{6}$` per FR-11c, the
    // CTA must always emit a URL-safe deep-link.
    render(<ClearanceGrantedCeremony linkCode="A B+C" />)
    const cta = screen.getByTestId("ceremony-cta") as HTMLAnchorElement
    expect(cta.href).toBe("https://t.me/Nikita_my_bot?start=A%20B%2BC")
  })
})
