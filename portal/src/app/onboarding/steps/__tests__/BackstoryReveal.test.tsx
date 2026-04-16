import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

// Mock the onboarding API hook; we only exercise previewBackstory + selectBackstory.
vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => {
  return {
    useOnboardingAPI: () => ({
      previewBackstory: previewBackstoryMock,
      submitProfile: vi.fn(),
      patchProfile: vi.fn(),
      selectBackstory: selectBackstoryMock,
    }),
  }
})

let previewBackstoryMock = vi.fn()
let selectBackstoryMock = vi.fn()

import { BackstoryReveal } from "@/app/onboarding/steps/BackstoryReveal"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"
import type {
  BackstoryOption,
  BackstoryPreviewResponse,
} from "@/app/onboarding/types/contracts"

// Spec 214 PR 214-B — T205 (RED)
// Tests:
//   AC-4.1: POST /preview-backstory called once on mount; loading state shown.
//   AC-4.2: 3 scenario cards render; clicking sets it as selected.
//   AC-4.3: degraded path (empty scenarios OR degraded:true) shows
//            ANALYSIS: PENDING stamp and advances.
//   AC-4.4: 429 rate-limit error displays exact Nikita-voiced copy.
//   AC-4.5: focus moves to the first scenario card (role="radio") after
//            the response lands.
//   AC-9.1: selecting a card marks it with CONFIRMED.
//   AC-9.2: PUT /chosen-option fires only on CTA click (not on card select).
//   AC-9.3: tone badge colour differs per tone (rose / blue / amber).
//   AC-9.4: cards rendered inside <div role="radiogroup">.

const baseValues: WizardFormValues = {
  location_city: "Berlin",
  social_scene: "techno",
  drug_tolerance: 3,
  life_stage: "tech",
  interest: null,
  name: null,
  age: null,
  occupation: null,
  phone: null,
  chosen_option_id: null,
  cache_key: null,
}

const scenario = (over: Partial<BackstoryOption> = {}): BackstoryOption => ({
  id: "abc123def456",
  venue: "Berghain",
  context: "You were in line. I was leaving.",
  the_moment: "Eye contact across the bouncer.",
  unresolved_hook: "You never got my name.",
  tone: "romantic",
  ...over,
})

const threeScenarios = (): BackstoryPreviewResponse => ({
  scenarios: [
    scenario({ id: "id-a", venue: "Berghain", tone: "romantic" }),
    scenario({ id: "id-b", venue: "KitKat", tone: "chaotic" }),
    scenario({ id: "id-c", venue: "Tresor", tone: "intellectual" }),
  ],
  venues_used: ["Berghain", "KitKat", "Tresor"],
  cache_key: "v1:berlin:techno:3:tech:::",
  degraded: false,
})

describe("BackstoryReveal (Step 8) — loading", () => {
  beforeEach(() => {
    previewBackstoryMock = vi.fn(
      () => new Promise<BackstoryPreviewResponse>(() => {}) // never resolves — stays in loading
    )
    selectBackstoryMock = vi.fn()
  })

  it("shows the Nikita-voiced loading headline on mount (AC-4.1)", () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    expect(screen.getByText(WIZARD_COPY.backstory.loadingHeadline)).toBeInTheDocument()
  })

  it("calls previewBackstory exactly once on mount (AC-4.1)", () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    expect(previewBackstoryMock).toHaveBeenCalledTimes(1)
    expect(previewBackstoryMock).toHaveBeenCalledWith(
      expect.objectContaining({
        city: "Berlin",
        social_scene: "techno",
        darkness_level: 3,
      })
    )
  })
})

describe("BackstoryReveal (Step 8) — success path", () => {
  beforeEach(() => {
    previewBackstoryMock = vi.fn().mockResolvedValue(threeScenarios())
    selectBackstoryMock = vi.fn().mockResolvedValue({
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    })
  })

  it("renders 3 scenario cards inside a role='radiogroup' (AC-4.2, AC-9.4)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByRole("radiogroup")).toBeInTheDocument()
    })
    const radios = screen.getAllByRole("radio")
    expect(radios.length).toBe(3)
  })

  it("renders the canonical card headers SCENARIO A / B / C (FR-3)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    for (const header of WIZARD_COPY.backstory.cardHeaders) {
      await waitFor(() => expect(screen.getByText(header)).toBeInTheDocument())
    }
  })

  it("selecting a card marks it with the CONFIRMED stamp (AC-9.1)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const radios = await screen.findAllByRole("radio")
    fireEvent.click(radios[1])
    expect(screen.getByText(WIZARD_COPY.backstory.selectedStamp)).toBeInTheDocument()
  })

  it("selecting a card does NOT call selectBackstory — only CTA click does (AC-9.2)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const radios = await screen.findAllByRole("radio")
    fireEvent.click(radios[0])
    expect(selectBackstoryMock).not.toHaveBeenCalled()
  })

  it("CTA click calls selectBackstory with the chosen id + cache_key (AC-9.2, AC-10.1)", async () => {
    const onAdvance = vi.fn()
    render(<BackstoryReveal values={baseValues} onAdvance={onAdvance} />)
    const radios = await screen.findAllByRole("radio")
    fireEvent.click(radios[2])
    const cta = screen.getByRole("button", { name: WIZARD_COPY.backstory.ctaCards })
    fireEvent.click(cta)
    await waitFor(() => {
      expect(selectBackstoryMock).toHaveBeenCalledWith(
        "id-c",
        "v1:berlin:techno:3:tech:::"
      )
    })
  })

  it("CTA click advances with chosen_option_id + cache_key after select succeeds", async () => {
    const onAdvance = vi.fn()
    render(<BackstoryReveal values={baseValues} onAdvance={onAdvance} />)
    const radios = await screen.findAllByRole("radio")
    fireEvent.click(radios[0])
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.backstory.ctaCards }))
    await waitFor(() => {
      expect(onAdvance).toHaveBeenCalledWith(
        expect.objectContaining({
          chosen_option_id: "id-a",
          cache_key: "v1:berlin:techno:3:tech:::",
        })
      )
    })
  })

  it("moves focus to the first scenario card after the response resolves (AC-4.5)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const radios = await screen.findAllByRole("radio")
    // After mount-effect, the first radio should be focused
    await waitFor(() => {
      expect(radios[0]).toHaveFocus()
    })
  })
})

describe("BackstoryReveal (Step 8) — degraded path (AC-4.3)", () => {
  it("shows ANALYSIS: PENDING stamp when scenarios is empty", async () => {
    previewBackstoryMock = vi.fn().mockResolvedValue({
      scenarios: [],
      venues_used: [],
      cache_key: "k",
      degraded: false,
    })
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(WIZARD_COPY.backstory.degradedHeadline)).toBeInTheDocument()
    })
  })

  it("shows ANALYSIS: PENDING stamp when degraded=true is flagged by backend", async () => {
    previewBackstoryMock = vi.fn().mockResolvedValue({
      scenarios: [],
      venues_used: [],
      cache_key: "k",
      degraded: true,
    })
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(WIZARD_COPY.backstory.degradedHeadline)).toBeInTheDocument()
    })
  })

  it("advances on the degraded CTA click (Understood.) without calling selectBackstory", async () => {
    previewBackstoryMock = vi.fn().mockResolvedValue({
      scenarios: [],
      venues_used: [],
      cache_key: "k",
      degraded: true,
    })
    selectBackstoryMock = vi.fn()
    const onAdvance = vi.fn()
    render(<BackstoryReveal values={baseValues} onAdvance={onAdvance} />)
    const cta = await screen.findByRole("button", {
      name: WIZARD_COPY.backstory.ctaDegraded,
    })
    fireEvent.click(cta)
    expect(selectBackstoryMock).not.toHaveBeenCalled()
    expect(onAdvance).toHaveBeenCalled()
  })
})

describe("BackstoryReveal (Step 8) — rate limit 429 (AC-4.4, AC-3.3)", () => {
  it("surfaces the exact Nikita-voiced 429 message", async () => {
    previewBackstoryMock = vi.fn().mockRejectedValue({
      status: 429,
      detail: "rate limit",
    })
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(WIZARD_COPY.backstory.rateLimitError)).toBeInTheDocument()
    })
  })
})
