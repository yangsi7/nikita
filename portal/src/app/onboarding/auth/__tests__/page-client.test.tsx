import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import OnboardingAuthClient from "../page-client"
import { toast } from "sonner"

// Spec 214 PR #310 (entry-wiring): /onboarding/auth is the Nikita-voiced
// magic-link landing page (FR-1 step 2). The form must dispatch a Supabase
// magic link whose emailRedirectTo carries `next=/onboarding`, so the auth
// callback bounces the user into the wizard rather than the dashboard.

const mockSignInWithOtp = vi.fn()
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { signInWithOtp: mockSignInWithOtp },
  }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe("OnboardingAuthClient — Spec 214 FR-1 step 2 (PR #310)", () => {
  beforeEach(() => {
    mockSignInWithOtp.mockReset()
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it("renders an email input and a submit CTA", () => {
    render(<OnboardingAuthClient />)
    const inputs = document.querySelectorAll('input[type="email"]')
    expect(inputs.length).toBeGreaterThan(0)
    const buttons = screen.getAllByRole("button")
    expect(buttons.length).toBeGreaterThan(0)
  })

  it("uses Nikita-voiced copy (no SaaS-phrase substrings anywhere on screen)", () => {
    const { container } = render(<OnboardingAuthClient />)
    // Spec 214 FR-3 bans generic SaaS phrasing across all wizard surfaces.
    // Tolerant separator class `[\s-]?` catches `signin`, `sign-in`, and
    // `sign in` so the regex doesn't miss hyphenated/concatenated leaks.
    const text = container.textContent ?? ""
    expect(text).not.toMatch(/sign[\s-]?in/i)
    expect(text).not.toMatch(/sign[\s-]?up/i)
    expect(text).not.toMatch(/get[\s-]?started/i)
    expect(text).not.toMatch(/log[\s-]?in/i)
  })

  it("dispatches signInWithOtp with emailRedirectTo carrying next=/onboarding", async () => {
    mockSignInWithOtp.mockResolvedValue({ error: null })
    const { container } = render(<OnboardingAuthClient />)

    const input = container.querySelector('input[type="email"]') as HTMLInputElement
    expect(input).toBeTruthy()
    fireEvent.change(input, { target: { value: "test@example.com" } })

    const form = container.querySelector("form") as HTMLFormElement
    expect(form).toBeTruthy()
    fireEvent.submit(form)

    await waitFor(() => {
      expect(mockSignInWithOtp).toHaveBeenCalledTimes(1)
    })
    const callArg = mockSignInWithOtp.mock.calls[0][0]
    expect(callArg.email).toBe("test@example.com")
    // The redirect URL is built via encodeURIComponent("/onboarding"), so
    // the slash is always percent-encoded — assert the exact wire format.
    expect(callArg.options.emailRedirectTo).toMatch(
      /\/auth\/callback\?next=%2Fonboarding/,
    )
  })

  it("shows a 'sent' confirmation state after a successful submit", async () => {
    mockSignInWithOtp.mockResolvedValue({ error: null })
    const { container } = render(<OnboardingAuthClient />)

    const input = container.querySelector('input[type="email"]') as HTMLInputElement
    fireEvent.change(input, { target: { value: "test@example.com" } })
    const form = container.querySelector("form") as HTMLFormElement
    fireEvent.submit(form)

    await waitFor(() => {
      // Form should be replaced; the email address should appear in the
      // confirmation copy so the user knows where to look.
      expect(screen.getByText(/test@example\.com/)).toBeInTheDocument()
    })
  })

  it("classifies rate-limit errors with the exact spec'd Nikita-voiced toast", async () => {
    mockSignInWithOtp.mockResolvedValue({
      error: { message: "rate limit exceeded" },
    })
    const { container } = render(<OnboardingAuthClient />)

    const input = container.querySelector('input[type="email"]') as HTMLInputElement
    fireEvent.change(input, { target: { value: "test@example.com" } })
    const form = container.querySelector("form") as HTMLFormElement
    fireEvent.submit(form)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledTimes(1)
    })
    // Exact copy assertions — surface drift in the spec'd Nikita voice.
    expect(toast.error).toHaveBeenCalledWith(
      "Slow down. She doesn't like impatient.",
      { description: "Wait a moment before asking again." },
    )
  })

  it("classifies database/identity errors with the exact spec'd Nikita-voiced toast", async () => {
    mockSignInWithOtp.mockResolvedValue({
      error: { message: "Database error: identity not found" },
    })
    const { container } = render(<OnboardingAuthClient />)

    const input = container.querySelector('input[type="email"]') as HTMLInputElement
    fireEvent.change(input, { target: { value: "test@example.com" } })
    const form = container.querySelector("form") as HTMLFormElement
    fireEvent.submit(form)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledTimes(1)
    })
    expect(toast.error).toHaveBeenCalledWith(
      "Something went wrong on my end.",
      { description: "Try again or get in touch." },
    )
  })

  it("rate-limit classification wins when message contains BOTH database AND rate substrings", async () => {
    // Defends the order swap: a Supabase-style "database error: rate limit
    // exceeded" payload must be classified as rate-limit, not as an
    // account-state issue. handleResend orders rate-first too — symmetry.
    mockSignInWithOtp.mockResolvedValue({
      error: { message: "database error: rate limit exceeded" },
    })
    const { container } = render(<OnboardingAuthClient />)

    const input = container.querySelector('input[type="email"]') as HTMLInputElement
    fireEvent.change(input, { target: { value: "test@example.com" } })
    const form = container.querySelector("form") as HTMLFormElement
    fireEvent.submit(form)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledTimes(1)
    })
    expect(toast.error).toHaveBeenCalledWith(
      "Slow down. She doesn't like impatient.",
      expect.anything(),
    )
  })
})
