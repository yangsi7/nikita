import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"

// Mock next/navigation BEFORE importing the component.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

// Mock the answer API hook so the WizardShell mounts without a real fetch.
const getStateMock = vi.fn()
const submitAnswerMock = vi.fn()
vi.mock("@/app/onboarding/hooks/use-answer-api", () => ({
  useAnswerAPI: () => ({
    getState: getStateMock,
    submitAnswer: submitAnswerMock,
  }),
}))

import { WizardShell } from "@/app/onboarding/_components/WizardShell"

describe("WizardShell — AC C1.4 / C1.13 / C1.15", () => {
  beforeEach(() => {
    getStateMock.mockReset()
    submitAnswerMock.mockReset()
    getStateMock.mockResolvedValue({
      last_assistant_turn: null,
      progress_pct: 0,
      is_complete: false,
      link_code: null,
      elided_extracted: {},
      conversation_id: null,
    })
  })

  it("calls GET /onboarding/state on mount (resume hydration C1.15)", async () => {
    render(<WizardShell />)
    await waitFor(() => expect(getStateMock).toHaveBeenCalledTimes(1))
  })

  it("renders the wizard landmark with aria-label", async () => {
    render(<WizardShell />)
    await waitFor(() => {
      expect(
        screen.getByRole("main", { name: /onboarding wizard/i })
      ).toBeInTheDocument()
    })
  })

  it("renders the welcome screen headline first", async () => {
    render(<WizardShell />)
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /let's begin/i })
      ).toBeInTheDocument()
    })
  })

  it("renders the ProgressRail at 0% on cold start", async () => {
    render(<WizardShell />)
    await waitFor(() => {
      const bar = screen.getByRole("progressbar", { name: /onboarding progress/i })
      expect(bar).toHaveAttribute("aria-valuenow", "0")
    })
  })

  it("animates ProgressRail to resumed pct on hydration (C1.15)", async () => {
    getStateMock.mockResolvedValueOnce({
      last_assistant_turn: { role: "nikita", content: "welcome back." },
      progress_pct: 50,
      is_complete: false,
      link_code: null,
      elided_extracted: {},
      conversation_id: "conv-1",
    })
    render(<WizardShell />)
    await waitFor(() => {
      const bar = screen.getByRole("progressbar", { name: /onboarding progress/i })
      expect(bar).toHaveAttribute("aria-valuenow", "50")
    })
  })
})
