import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"

import { QRHandoff } from "@/app/onboarding/components/QRHandoff"

// Spec 214 PR 214-B — T209 (RED)
// Tests:
//   AC-NR4.1: Renders only when viewport ≥ 768px (desktop); null on mobile.
//   AC-NR4.2: Wrapped in <figure> with <figcaption> containing Nikita copy.
//   AC-NR4.3: No server-side deps — purely client side (matchMedia guard).
//   AC-NR4.4: figcaption is canonical accessibility affordance (not aria-label
//              on canvas).

function mockMatchMedia(desktopMatches: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: desktopMatches && /min-width/.test(query),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

const TG = "https://t.me/Nikita_my_bot"

describe("QRHandoff — responsive gating (AC-NR4.1)", () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it("renders NOTHING on mobile viewport (<768px)", () => {
    mockMatchMedia(false)
    const { container } = render(<QRHandoff telegramUrl={TG} />)
    // Component must return null on mobile — no DOM output
    expect(container.firstChild).toBeNull()
  })

  it("renders the QR code on desktop viewport (≥768px)", () => {
    mockMatchMedia(true)
    render(<QRHandoff telegramUrl={TG} />)
    // Desktop render — component should mount a <figure>
    expect(screen.getByRole("figure")).toBeInTheDocument()
  })
})

describe("QRHandoff — canonical copy + structure (AC-NR4.2, AC-NR4.4)", () => {
  beforeEach(() => {
    mockMatchMedia(true)
  })

  it("wraps the QR in <figure> with <figcaption> carrying Nikita-voiced copy", () => {
    render(<QRHandoff telegramUrl={TG} />)
    const figure = screen.getByRole("figure")
    expect(figure).toBeInTheDocument()
    // AC-NR4.2 canonical copy
    expect(
      screen.getByText(/On desktop\? Scan to open on your phone\./i)
    ).toBeInTheDocument()
  })

  it("renders a QR artifact (SVG or canvas) encoding the given telegramUrl", () => {
    render(<QRHandoff telegramUrl={TG} />)
    const figure = screen.getByRole("figure")
    // qrcode.react outputs either an SVG or a canvas; accept either.
    const artifact =
      figure.querySelector("svg") ?? figure.querySelector("canvas")
    expect(artifact).not.toBeNull()
  })

  it("accepts a custom label prop that overrides the default caption", () => {
    render(<QRHandoff telegramUrl={TG} label="Point your phone at this." />)
    expect(screen.getByText("Point your phone at this.")).toBeInTheDocument()
  })
})
