import { describe, expect, it, vi, beforeEach } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

// Mock next/navigation BEFORE importing the component.
const routerPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush, replace: vi.fn() }),
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

function emptyState() {
  return {
    last_assistant_turn: null,
    progress_pct: 0,
    is_complete: false,
    link_code: null,
    elided_extracted: {},
    conversation_id: null,
  }
}

function successResponse(overrides: Record<string, unknown> = {}) {
  return {
    output: {
      kind: "success" as const,
      delta: null,
      reply: "okay.",
      next_slot_kind: null,
    },
    progress_pct: 10,
    is_complete: false,
    link_code: null,
    conversation_id: "conv-1",
    meta: null,
    ...overrides,
  }
}

describe("WizardShell — AC C1.4 / C1.13 / C1.15", () => {
  beforeEach(() => {
    getStateMock.mockReset()
    submitAnswerMock.mockReset()
    routerPush.mockReset()
    getStateMock.mockResolvedValue(emptyState())
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
      const bar = screen.getByRole("progressbar", {
        name: /onboarding progress/i,
      })
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
      const bar = screen.getByRole("progressbar", {
        name: /onboarding progress/i,
      })
      expect(bar).toHaveAttribute("aria-valuenow", "50")
    })
  })
})

// -----------------------------------------------------------------------------
// Walk A1 H2 — wizard rehydration shows next missing slot, not welcome screen.
// Closes GH #485. Anti-pattern (pre-fix): the mount effect fetched
// /onboarding/state but did not map progress_pct → screenIndex, so revisit
// at progress > 0 always rendered the welcome screen "let's begin." instead of
// resuming at the next missing slot.
// -----------------------------------------------------------------------------

describe("WizardShell — Walk A1 H2 rehydration resumes at next slot", () => {
  beforeEach(() => {
    getStateMock.mockReset()
    submitAnswerMock.mockReset()
    routerPush.mockReset()
  })

  it("resume_at_next_slot_when_state_hydrates_with_progress: progress_pct=23 (3/13 slots) → occupation screen, not welcome", async () => {
    // 23% of 13 slots ≈ 3 filled (display_name, age, city). Next slot is
    // occupation (screen 4 in WIZARD_SCREENS). Welcome screen ("let's begin.")
    // must NOT render.
    getStateMock.mockResolvedValueOnce({
      last_assistant_turn: { role: "nikita", content: "what do you do?" },
      progress_pct: 23,
      is_complete: false,
      link_code: null,
      elided_extracted: {
        display_name: "Walker",
        age: 28,
        city: "Zürich",
      },
      conversation_id: "conv-1",
    })
    render(<WizardShell />)
    await waitFor(() => {
      // Occupation screen headline.
      expect(
        screen.getByRole("heading", { name: /what do you do\?/i })
      ).toBeInTheDocument()
    })
    // Welcome screen headline must NOT be present.
    expect(
      screen.queryByRole("heading", { name: /let's begin/i })
    ).not.toBeInTheDocument()
  })

  it("fresh_signup_shows_welcome_when_state_empty: progress_pct=0 → welcome screen", async () => {
    getStateMock.mockResolvedValueOnce(emptyState())
    render(<WizardShell />)
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /let's begin/i })
      ).toBeInTheDocument()
    })
  })
})

describe("WizardShell — Continue gating per slot (I6)", () => {
  beforeEach(() => {
    getStateMock.mockReset()
    submitAnswerMock.mockReset()
    routerPush.mockReset()
    getStateMock.mockResolvedValue(emptyState())
  })

  it("welcome 'begin' button is enabled by default", async () => {
    render(<WizardShell />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^begin$/i })).toBeEnabled()
    })
  })

  it("display_name screen disables continue when input is empty", async () => {
    render(<WizardShell />)
    await waitFor(() => screen.getByRole("button", { name: /begin/i }))
    fireEvent.click(screen.getByRole("button", { name: /begin/i }))
    await waitFor(() =>
      screen.getByRole("heading", { name: /what should she call you/i })
    )
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/your name/i), {
      target: { value: "alex" },
    })
    expect(screen.getByRole("button", { name: /continue/i })).toBeEnabled()
  })
})

describe("WizardShell — error banner on failed POST (I6)", () => {
  beforeEach(() => {
    getStateMock.mockReset()
    submitAnswerMock.mockReset()
    routerPush.mockReset()
    getStateMock.mockResolvedValue(emptyState())
  })

  it("renders the rose-toned error banner when submitAnswer rejects with 5xx", async () => {
    submitAnswerMock.mockRejectedValueOnce({ status: 500, detail: "boom" })
    render(<WizardShell />)
    await waitFor(() => screen.getByRole("button", { name: /begin/i }))
    fireEvent.click(screen.getByRole("button", { name: /begin/i }))
    await waitFor(() => screen.getByLabelText(/your name/i))
    fireEvent.change(screen.getByLabelText(/your name/i), {
      target: { value: "alex" },
    })
    fireEvent.click(screen.getByRole("button", { name: /continue/i }))
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/try again/i)
    })
  })
})

describe("WizardShell — turn_id idempotency cache (I2)", () => {
  beforeEach(() => {
    getStateMock.mockReset()
    submitAnswerMock.mockReset()
    routerPush.mockReset()
    getStateMock.mockResolvedValue(emptyState())
  })

  it("retry after a transient failure reuses the same turn_id", async () => {
    submitAnswerMock
      .mockRejectedValueOnce({ status: 500 })
      .mockResolvedValueOnce(successResponse())
    render(<WizardShell />)
    await waitFor(() => screen.getByRole("button", { name: /begin/i }))
    fireEvent.click(screen.getByRole("button", { name: /begin/i }))
    await waitFor(() => screen.getByLabelText(/your name/i))
    fireEvent.change(screen.getByLabelText(/your name/i), {
      target: { value: "alex" },
    })
    fireEvent.click(screen.getByRole("button", { name: /continue/i }))
    await waitFor(() => screen.getByRole("alert"))
    // Retry — Continue is still enabled (the input is still valid).
    fireEvent.click(screen.getByRole("button", { name: /continue/i }))
    await waitFor(() => expect(submitAnswerMock).toHaveBeenCalledTimes(2))
    const turn1 = submitAnswerMock.mock.calls[0]?.[0]?.turn_id as string | undefined
    const turn2 = submitAnswerMock.mock.calls[1]?.[0]?.turn_id as string | undefined
    expect(turn1).toBeTruthy()
    expect(turn2).toBe(turn1)
  })
})
