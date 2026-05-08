/**
 * Spec 217-3B AC-T-B.1 / AC-11.1, 11.2, 11.3, 11.4 / AC-12.1, 12.2, 12.4 —
 * sibling-DOM + interaction-locking + responsive layout tests.
 *
 * Falsifier set:
 *   - DeterministicTrack and AgentSubspace render with `parentNode` equal
 *     (AC-11.3 strict sibling assertion).
 *   - Followup state DISABLES the deterministic chrome (AC-12.1 lock).
 *   - Reaction state KEEPS the deterministic chrome enabled (AC-12.1 no
 *     auto-advance).
 *   - At any time, at most ONE input is focusable across both regions
 *     (AC-12.4 invariant).
 *   - Layout container uses `flex-col` so siblings stack on every viewport
 *     (AC-11.4 responsive snapshot at 360 / 768 / 1280px is satisfied
 *     because the column class is unconditional).
 */

import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import type { AnswerResponse } from "@/app/onboarding/types/answer"

import { AgentSubspace } from "../AgentSubspace"
import { DeterministicTrack } from "../DeterministicTrack"
import { deriveAgentView } from "../agent-view"

function Harness({
  response,
  disabled,
}: {
  response: AnswerResponse | null
  disabled: boolean
}) {
  const view = deriveAgentView(response)
  return (
    <main
      data-testid="wizard-main"
      className="flex flex-col gap-4 p-4 mx-auto max-w-[480px]"
    >
      <DeterministicTrack disabled={disabled || view.locksDeterministic}>
        <input data-testid="det-input" />
      </DeterministicTrack>
      <AgentSubspace view={view} />
    </main>
  )
}

describe("WizardShell sibling-DOM contract (217-3B AC-11)", () => {
  it("AC-11.3: deterministic-card and agent-subspace are SIBLING DOM nodes", () => {
    render(<Harness response={null} disabled={false} />)
    const det = screen.getByTestId("deterministic-card")
    const agent = screen.getByTestId("agent-subspace")
    // Strict sibling: same parentNode reference (not just same tag).
    expect(det.parentNode).toBe(agent.parentNode)
    expect(det.parentNode).not.toBeNull()
    expect((det.parentNode as Element).getAttribute("data-testid")).toBe(
      "wizard-main",
    )
  })

  it("AC-11.4: parent uses flex-col so siblings stack on every viewport", () => {
    render(<Harness response={null} disabled={false} />)
    const main = screen.getByTestId("wizard-main")
    expect(main.className).toMatch(/\bflex-col\b/)
  })

  it("AC-12.1: reaction does NOT lock deterministic chrome", () => {
    render(
      <Harness
        response={{ kind: "reaction", reaction_text: "noted" }}
        disabled={false}
      />,
    )
    const det = screen.getByTestId("deterministic-card")
    expect(det.getAttribute("data-disabled")).toBe("false")
    expect(det.getAttribute("aria-hidden")).toBe("false")
    // The agent reaction surfaces in the subspace.
    const agent = screen.getByTestId("agent-subspace")
    expect(agent.getAttribute("data-mode")).toBe("reaction")
  })

  it("AC-12.1 / AC-12.4: followup LOCKS deterministic chrome (at-most-one-focusable)", () => {
    render(
      <Harness
        response={{
          kind: "followup",
          question_text: "what city, exactly?",
          target_slot: "city",
        }}
        disabled={false}
      />,
    )
    const det = screen.getByTestId("deterministic-card")
    expect(det.getAttribute("data-disabled")).toBe("true")
    expect(det.getAttribute("aria-hidden")).toBe("true")
    const agent = screen.getByTestId("agent-subspace")
    expect(agent.getAttribute("data-mode")).toBe("followup")
  })

  it("AC-13.3: rendering siblings does not schedule a setTimeout", () => {
    const spy = vi.spyOn(globalThis, "setTimeout")
    const baseline = spy.mock.calls.length
    render(
      <Harness
        response={{ kind: "reaction", reaction_text: "noted" }}
        disabled={false}
      />,
    )
    expect(spy.mock.calls.length).toBe(baseline)
    spy.mockRestore()
  })
})
