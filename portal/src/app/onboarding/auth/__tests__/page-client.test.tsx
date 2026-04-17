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
    // Anchored regex would only catch standalone words; substring regex
    // catches accidental leaks like "Please sign in here" too.
    const text = container.textContent ?? ""
    expect(text).not.toMatch(/\bsign in\b/i)
    expect(text).not.toMatch(/\bsign up\b/i)
    expect(text).not.toMatch(/\bget started\b/i)
    expect(text).not.toMatch(/\blog in\b/i)
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

  it("classifies rate-limit errors with Nikita-voiced toast (no generic SaaS error)", async () => {
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
    const [title, opts] = vi.mocked(toast.error).mock.calls[0]
    expect(title).toMatch(/slow down|impatient/i)
    expect(opts).toMatchObject({ description: expect.stringMatching(/wait|moment/i) })
  })

  it("classifies database/identity errors distinctly from generic failures", async () => {
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
    const [title] = vi.mocked(toast.error).mock.calls[0]
    expect(title).toMatch(/file/i)
    expect(title).not.toMatch(/door wouldn/i)
  })
})
