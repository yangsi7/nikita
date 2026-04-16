import { createElement } from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor, act } from "@testing-library/react"

// Override the global framer-motion mock so useReducedMotion is exported.
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

// Mock the pipeline-ready hook — the step consumes its state directly.
vi.mock("@/app/onboarding/hooks/use-pipeline-ready", () => {
  return {
    useOnboardingPipelineReady: () => pipelineReadyMock(),
  }
})

let pipelineReadyMock: () => Record<string, unknown> = () => ({
  state: "pending",
  venueResearchStatus: "pending",
  backstoryAvailable: false,
  wizardStep: null,
  timedOut: false,
  error: null,
})

// Mock useOnboardingAPI for the POST /profile call on mount.
vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => {
  return {
    useOnboardingAPI: () => ({
      previewBackstory: vi.fn(),
      submitProfile: submitProfileMock,
      patchProfile: vi.fn(),
      selectBackstory: vi.fn(),
    }),
  }
})

let submitProfileMock = vi.fn()

import { PipelineGate } from "@/app/onboarding/steps/PipelineGate"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-B — T207 (RED)
// Tests:
//   AC-5.1..5.3: poll state transitions render correct UI.
//   AC-5.4: data-testid="pipeline-gate-stamp" carries data-state attribute.
//   AC-7.2: HTTP 409 — rewind to step 9 (surfaced via onAdvance with step hint).
//   AC-7.3: HTTP 422 — display failed toast copy.
//   AC-3.3: the 422 path must show the canonical Nikita-voiced copy.
//   prefers-reduced-motion: animations skipped.

const readyValues: WizardFormValues = {
  location_city: "Berlin",
  social_scene: "techno",
  drug_tolerance: 3,
  life_stage: "tech",
  interest: null,
  name: null,
  age: null,
  occupation: null,
  phone: null,
  chosen_option_id: "id-a",
  cache_key: "k1",
}

describe("PipelineGate (Step 10) — pending state", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
    submitProfileMock = vi.fn().mockResolvedValue({
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    pipelineReadyMock = () => ({
      state: "pending",
      venueResearchStatus: "pending",
      backstoryAvailable: false,
      wizardStep: null,
      timedOut: false,
      error: null,
    })
  })

  it("renders with data-testid='wizard-step-10' (AC-1.5)", () => {
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    expect(screen.getByTestId("wizard-step-10")).toBeInTheDocument()
  })

  it("shows the PENDING stamp with data-state='pending' (AC-5.4)", () => {
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    const stamp = screen.getByTestId("pipeline-gate-stamp")
    expect(stamp).toBeInTheDocument()
    expect(stamp).toHaveAttribute("data-state", "pending")
    expect(screen.getByText(WIZARD_COPY.pipelineGate.headline)).toBeInTheDocument()
  })

  it("posts the full profile on mount (FR-7 / AC-7.1)", () => {
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    expect(submitProfileMock).toHaveBeenCalledTimes(1)
    expect(submitProfileMock).toHaveBeenCalledWith(
      expect.objectContaining({ wizard_step: 10 })
    )
  })
})

describe("PipelineGate (Step 10) — ready state (AC-5.2, AC-5.4)", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
    submitProfileMock = vi.fn().mockResolvedValue({
      user_id: "u",
      pipeline_state: "ready",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    pipelineReadyMock = () => ({
      state: "ready",
      venueResearchStatus: "complete",
      backstoryAvailable: true,
      wizardStep: null,
      timedOut: false,
      error: null,
    })
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("shows CLEARED stamp with data-state='ready'", () => {
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    const stamp = screen.getByTestId("pipeline-gate-stamp")
    expect(stamp).toHaveAttribute("data-state", "ready")
  })

  it("auto-advances ~1.5s after reaching ready state", () => {
    const onAdvance = vi.fn()
    render(<PipelineGate values={readyValues} onAdvance={onAdvance} userId="u" />)
    // Not advanced yet
    expect(onAdvance).not.toHaveBeenCalled()
    act(() => {
      vi.advanceTimersByTime(1500)
    })
    expect(onAdvance).toHaveBeenCalled()
  })
})

describe("PipelineGate (Step 10) — degraded / timeout (AC-5.3)", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
    submitProfileMock = vi.fn().mockResolvedValue({
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
  })

  it("shows PROVISIONAL — CLEARED with data-state='degraded' for degraded responses", () => {
    pipelineReadyMock = () => ({
      state: "degraded",
      venueResearchStatus: "failed",
      backstoryAvailable: false,
      wizardStep: null,
      timedOut: false,
      error: null,
    })
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    const stamp = screen.getByTestId("pipeline-gate-stamp")
    expect(stamp).toHaveAttribute("data-state", "degraded")
    expect(
      screen.getByText(WIZARD_COPY.pipelineGate.degradedStamp)
    ).toBeInTheDocument()
  })

  it("shows PROVISIONAL — CLEARED with data-state='timeout' when timedOut is true", () => {
    pipelineReadyMock = () => ({
      state: "pending",
      venueResearchStatus: "pending",
      backstoryAvailable: false,
      wizardStep: null,
      timedOut: true,
      error: null,
    })
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    const stamp = screen.getByTestId("pipeline-gate-stamp")
    expect(stamp).toHaveAttribute("data-state", "timeout")
  })
})

describe("PipelineGate (Step 10) — error paths (AC-7.2, AC-7.3, AC-3.3)", () => {
  beforeEach(() => {
    reducedMotionMock = () => false
    pipelineReadyMock = () => ({
      state: "pending",
      venueResearchStatus: "pending",
      backstoryAvailable: false,
      wizardStep: null,
      timedOut: false,
      error: null,
    })
  })

  it("renders the Nikita-voiced 422 toast copy on submit failure (AC-7.3, AC-3.3)", async () => {
    submitProfileMock = vi.fn().mockRejectedValue({ status: 422, detail: "bad" })
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    await waitFor(() => {
      expect(
        screen.getByText(WIZARD_COPY.pipelineGate.failedToast)
      ).toBeInTheDocument()
    })
  })

  it("exposes data-testid='pipeline-gate-409' with rewind hint on duplicate phone (AC-7.2)", async () => {
    submitProfileMock = vi.fn().mockRejectedValue({ status: 409, detail: "dup" })
    const onAdvance = vi.fn()
    render(<PipelineGate values={readyValues} onAdvance={onAdvance} userId="u" />)
    // Rewind surface: the gate surfaces data-testid="pipeline-gate-409" so the
    // orchestrator can rewind to step 9.
    await waitFor(() => {
      expect(screen.getByTestId("pipeline-gate-409")).toBeInTheDocument()
    })
  })
})

describe("PipelineGate (Step 10) — prefers-reduced-motion", () => {
  beforeEach(() => {
    reducedMotionMock = () => true
    submitProfileMock = vi.fn().mockResolvedValue({
      user_id: "u",
      pipeline_state: "ready",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
    pipelineReadyMock = () => ({
      state: "ready",
      venueResearchStatus: "complete",
      backstoryAvailable: true,
      wizardStep: null,
      timedOut: false,
      error: null,
    })
  })

  it("renders final stamp state immediately when reduced motion is on", () => {
    render(<PipelineGate values={readyValues} onAdvance={vi.fn()} userId="u" />)
    // Stamp must be visible on first paint (no animation wait)
    expect(screen.getByText(WIZARD_COPY.pipelineGate.readyStamp)).toBeInTheDocument()
  })
})
