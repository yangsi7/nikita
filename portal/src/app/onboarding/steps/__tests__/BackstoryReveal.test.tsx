import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

// Mock the onboarding API hook; we only exercise previewBackstory + selectBackstory.
vi.mock("@/app/onboarding/hooks/use-onboarding-api", () => {
  return {
    useOnboardingAPI: () => ({
      previewBackstory: previewBackstoryMock,
      submitProfile: vi.fn(),
      patchProfile: patchProfileMock,
      selectBackstory: selectBackstoryMock,
    }),
  }
})

let previewBackstoryMock = vi.fn()
let selectBackstoryMock = vi.fn()
// GH #313 regression guard. Named mock so the call-order test below can
// `callOrder.push("patch")` before the wrapped selectBackstoryMock runs.
let patchProfileMock = vi.fn()

import { BackstoryReveal } from "@/app/onboarding/steps/BackstoryReveal"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { WizardFormValues } from "@/app/onboarding/types/wizard"
import type {
  BackstoryOption,
  BackstoryPreviewResponse,
  OnboardingV2ProfileResponse,
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
    // GH #313 guard: default to a resolved patchProfile so existing tests
    // (which don't care about it) still pass through the new await. Tests
    // that need custom behaviour override this in-body. Typed against the
    // response contract so a future shape drift breaks loudly rather than
    // hiding behind `as unknown as`.
    const resolvedPatch: OnboardingV2ProfileResponse = {
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    }
    patchProfileMock = vi.fn().mockResolvedValue(resolvedPatch)
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

  // GH #313 regression guard for the Clearance-mismatch 403.
  //
  // Root cause (2026-04-17 Agent H dogfood walk): BackstoryReveal's CTA
  // fired PUT /profile/chosen-option BEFORE any PATCH /profile had populated
  // user.onboarding_profile JSONB. The backend recomputed cache_key from an
  // empty JSONB (all fields `unknown`), the submitted key carried real values
  // (city|scene|darkness|...), they mismatched, backend returned
  // 403 "Clearance mismatch. Start over." The wizard was permanently stuck.
  //
  // Fix contract: confirmAndAdvance MUST
  //   (1) call patchProfile with the full collected profile first,
  //   (2) await it to completion (not fire-and-forget; server must persist
  //       before the PUT recomputes the key),
  //   (3) THEN call selectBackstory with (chosen_option_id, cache_key).
  //
  // These three assertions are RED until the source fix lands. Each one
  // guards a distinct aspect (called-at-all / correct-payload / ordering)
  // so a partial regression (e.g., someone drops the await) still fails
  // exactly one assertion instead of hiding behind another passing case.
  it("CTA click calls patchProfile with collected values BEFORE selectBackstory (GH #313)", async () => {
    const onAdvance = vi.fn()
    const callOrder: string[] = []
    const response: OnboardingV2ProfileResponse = {
      user_id: "u",
      pipeline_state: "pending",
      backstory_options: [],
      chosen_option: null,
      poll_endpoint: "/api/v1/onboarding/pipeline-ready/u",
      poll_interval_seconds: 2,
      poll_max_wait_seconds: 20,
    }
    patchProfileMock = vi.fn(async () => {
      callOrder.push("patch")
      return response
    })
    selectBackstoryMock = vi.fn(async () => {
      callOrder.push("select")
      return response
    })
    render(<BackstoryReveal values={baseValues} onAdvance={onAdvance} />)
    const radios = await screen.findAllByRole("radio")
    fireEvent.click(radios[0])
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.backstory.ctaCards }))

    await waitFor(() => {
      expect(patchProfileMock).toHaveBeenCalledTimes(1)
    })
    // PATCH body must carry every collected wizard value so the backend's
    // compute_backstory_cache_key recompute sees the same inputs as the
    // client-side cache_key that's about to be submitted to selectBackstory.
    expect(patchProfileMock).toHaveBeenCalledWith(
      expect.objectContaining({
        location_city: "Berlin",
        social_scene: "techno",
        drug_tolerance: 3,
        life_stage: "tech",
      })
    )
    await waitFor(() => {
      expect(selectBackstoryMock).toHaveBeenCalledTimes(1)
    })
    // Call order is the load-bearing invariant. If selectBackstory runs
    // before patchProfile resolves, the server's JSONB is still empty,
    // the clearance check 403s, and we are back in the exact regression
    // this test is guarding against.
    expect(callOrder).toEqual(["patch", "select"])
  })

  it("abandons the advance (does NOT call selectBackstory) if patchProfile rejects", async () => {
    // If the server refuses the PATCH (e.g., 422 from a bad field), we must
    // NOT race forward to selectBackstory, because doing so would
    // re-introduce the clearance mismatch. The button re-enables so the
    // user can retry.
    const onAdvance = vi.fn()
    patchProfileMock = vi.fn().mockRejectedValue(new Error("boom"))
    selectBackstoryMock = vi.fn()
    render(<BackstoryReveal values={baseValues} onAdvance={onAdvance} />)
    const radios = await screen.findAllByRole("radio")
    fireEvent.click(radios[0])
    fireEvent.click(screen.getByRole("button", { name: WIZARD_COPY.backstory.ctaCards }))

    await waitFor(() => {
      expect(patchProfileMock).toHaveBeenCalledTimes(1)
    })
    expect(selectBackstoryMock).not.toHaveBeenCalled()
    expect(onAdvance).not.toHaveBeenCalled()
  })

  it("moves focus to the first scenario card after the response resolves (AC-4.5)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const radios = await screen.findAllByRole("radio")
    // After mount-effect, the first radio should be focused
    await waitFor(() => {
      expect(radios[0]).toHaveFocus()
    })
  })

  it("ArrowDown moves focus to the next card and wraps at end (AC-9.4 radiogroup)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const group = await screen.findByRole("radiogroup")
    const radios = await screen.findAllByRole("radio")
    await waitFor(() => expect(radios[0]).toHaveFocus())

    fireEvent.keyDown(group, { key: "ArrowDown" })
    expect(radios[1]).toHaveFocus()
    fireEvent.keyDown(group, { key: "ArrowDown" })
    expect(radios[2]).toHaveFocus()
    // Wrap to first
    fireEvent.keyDown(group, { key: "ArrowDown" })
    expect(radios[0]).toHaveFocus()
  })

  it("ArrowUp moves focus to the previous card and wraps at start (AC-9.4 radiogroup)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const group = await screen.findByRole("radiogroup")
    const radios = await screen.findAllByRole("radio")
    await waitFor(() => expect(radios[0]).toHaveFocus())

    // First ArrowUp wraps to the last card
    fireEvent.keyDown(group, { key: "ArrowUp" })
    expect(radios[2]).toHaveFocus()
    fireEvent.keyDown(group, { key: "ArrowUp" })
    expect(radios[1]).toHaveFocus()
  })

  it("Home/End jump focus to first/last card (AC-9.4 radiogroup)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const group = await screen.findByRole("radiogroup")
    const radios = await screen.findAllByRole("radio")
    await waitFor(() => expect(radios[0]).toHaveFocus())

    fireEvent.keyDown(group, { key: "End" })
    expect(radios[2]).toHaveFocus()
    fireEvent.keyDown(group, { key: "Home" })
    expect(radios[0]).toHaveFocus()
  })

  it("Space selects the focused card (AC-9.4 radiogroup)", async () => {
    render(<BackstoryReveal values={baseValues} onAdvance={vi.fn()} />)
    const group = await screen.findByRole("radiogroup")
    const radios = await screen.findAllByRole("radio")
    await waitFor(() => expect(radios[0]).toHaveFocus())

    fireEvent.keyDown(group, { key: "ArrowDown" })
    fireEvent.keyDown(group, { key: " " })
    expect(radios[1]).toHaveAttribute("aria-checked", "true")
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
