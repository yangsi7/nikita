import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

const pushMock = vi.fn()
const prefetchMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, prefetch: prefetchMock, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}))

import InterstitialClient from "../InterstitialClient"

beforeEach(() => {
  pushMock.mockReset()
  prefetchMock.mockReset()
  vi.useRealTimers()
})

describe("Spec 217-1 FR-2 — InterstitialClient brand veil + tap surface", () => {
  it("AC-2.1bis: tap surface is a native <button> with /tap to enter/i name", () => {
    render(<InterstitialClient requireGesture={true} next="/onboarding" />)
    const btn = screen.getByRole("button", { name: /tap to enter/i })
    expect(btn).toBeInTheDocument()
    expect(btn.tagName).toBe("BUTTON")
  })

  it("AC-2.2: real click handler calls router.push(next)", async () => {
    const user = userEvent.setup()
    render(<InterstitialClient requireGesture={true} next="/onboarding" />)
    const btn = screen.getByRole("button", { name: /tap to enter/i })
    await user.click(btn)
    expect(pushMock).toHaveBeenCalledWith("/onboarding")
  })

  it("AC-2.1bis keyboard activation: Enter/Space advance to /onboarding", async () => {
    const user = userEvent.setup()
    render(<InterstitialClient requireGesture={true} next="/onboarding" />)
    await user.tab()
    await user.keyboard("{Enter}")
    expect(pushMock).toHaveBeenCalledWith("/onboarding")
  })

  it("AC-2.3: requireGesture=true does NOT auto-advance (iOS/IAB/unknown)", async () => {
    vi.useFakeTimers()
    render(<InterstitialClient requireGesture={true} next="/onboarding" />)
    vi.advanceTimersByTime(2000)
    expect(pushMock).not.toHaveBeenCalled()
  })

  it("AC-2.3: requireGesture=false auto-advances (confirmed Chrome desktop)", async () => {
    vi.useFakeTimers()
    render(<InterstitialClient requireGesture={false} next="/onboarding" />)
    vi.advanceTimersByTime(200)
    expect(pushMock).toHaveBeenCalledWith("/onboarding")
  })

  it("AC-2.4bis: data-require-gesture attribute reflects server prop (true)", () => {
    const { container } = render(
      <InterstitialClient requireGesture={true} next="/onboarding" />,
    )
    expect(
      container.querySelector('[data-require-gesture="true"]'),
    ).toBeInTheDocument()
  })

  it("AC-2.4bis: data-require-gesture attribute reflects server prop (false)", () => {
    const { container } = render(
      <InterstitialClient requireGesture={false} next="/onboarding" />,
    )
    expect(
      container.querySelector('[data-require-gesture="false"]'),
    ).toBeInTheDocument()
  })

  it("AC-2.5: router.prefetch(next) invoked on mount", () => {
    render(<InterstitialClient requireGesture={true} next="/onboarding" />)
    expect(prefetchMock).toHaveBeenCalledWith("/onboarding")
  })

  it("renders brand veil (bg-void) wrapper", () => {
    const { container } = render(
      <InterstitialClient requireGesture={true} next="/onboarding" />,
    )
    expect(container.querySelector(".bg-void")).toBeInTheDocument()
  })

  it("rejects protocol-relative ?next (cross-origin guard preserved)", async () => {
    const user = userEvent.setup()
    render(<InterstitialClient requireGesture={true} next="//evil.com" />)
    const btn = screen.getByRole("button", { name: /tap to enter/i })
    await user.click(btn)
    expect(pushMock).toHaveBeenCalledWith("/dashboard")
  })

  it("rejects absolute https ?next (cross-origin guard preserved)", async () => {
    const user = userEvent.setup()
    render(<InterstitialClient requireGesture={true} next="https://evil.com" />)
    const btn = screen.getByRole("button", { name: /tap to enter/i })
    await user.click(btn)
    expect(pushMock).toHaveBeenCalledWith("/dashboard")
  })
})
