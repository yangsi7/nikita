import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import OnboardingAuthClient from "../page-client"

// Spec 214 PR #310 (entry-wiring): /onboarding/auth is the Nikita-voiced
// magic-link landing page (FR-1 step 2). The form must dispatch a Supabase
// magic link whose emailRedirectTo carries `next=/onboarding`, so the auth
// callback bounces the user into the wizard rather than the dashboard.

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}))

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
  })

  it("renders an email input and a submit CTA", () => {
    render(<OnboardingAuthClient />)
    const inputs = document.querySelectorAll('input[type="email"]')
    expect(inputs.length).toBeGreaterThan(0)
    const buttons = screen.getAllByRole("button")
    expect(buttons.length).toBeGreaterThan(0)
  })

  it("uses Nikita-voiced copy (no generic SaaS phrases)", () => {
    render(<OnboardingAuthClient />)
    // Banned phrases per Spec 214 FR-3 wizard-copy discipline
    expect(screen.queryByText(/^sign in$/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^sign up$/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^get started$/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^log in$/i)).not.toBeInTheDocument()
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
    // The redirect URL must instruct /auth/callback to send the user into the
    // wizard at /onboarding, not the default /dashboard. Encoded `%2F` or raw
    // `/` are both acceptable depending on URLSearchParams behavior.
    expect(callArg.options.emailRedirectTo).toMatch(
      /\/auth\/callback\?next=(%2F|\/)onboarding/,
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
})
