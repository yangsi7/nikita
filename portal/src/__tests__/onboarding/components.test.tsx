import { createElement } from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

// Override global framer-motion mock to add useReducedMotion
vi.mock("framer-motion", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, react/display-name
  const mc = (tag: string) => ({ children, ...p }: any) => createElement(tag, p, children)
  const motion = new Proxy({}, { get: (_: object, t: string) => mc(t) })
  return { motion, useInView: () => true, useReducedMotion: () => false,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children }
})

vi.mock("@/components/ui/slider", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Slider: ({ min, max, step, value, onValueChange, ...p }: any) =>
    createElement("input", { type: "range", min, max, step, value: value?.[0],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => onValueChange?.([Number(e.target.value)]),
      "aria-label": p["aria-label"], "data-testid": "edginess-slider" }),
}))

import { EdginessSlider } from "@/app/onboarding/components/legacy/edginess-slider"
import { SceneSelector } from "@/app/onboarding/components/legacy/scene-selector"

// ChapterStepper tests removed in PR #298 (Spec 214 PR 214-B) — the cinematic
// layout that hosted this component was deleted; chapter-stepper.tsx is no
// longer part of the onboarding surface. The wizard layout (PR 214-C) does
// not re-introduce chapter progression UI. See GH #300.

describe("EdginessSlider", () => {
  it("renders level label and correct range", () => {
    render(<EdginessSlider value={3} onChange={vi.fn()} />)
    expect(screen.getByText("Spicy is okay")).toBeInTheDocument()
    const s = screen.getByTestId("edginess-slider") as HTMLInputElement
    expect(s.min).toBe("1")
    expect(s.max).toBe("5")
  })

  it("fires onChange with new value", () => {
    const onChange = vi.fn()
    render(<EdginessSlider value={3} onChange={onChange} />)
    fireEvent.change(screen.getByTestId("edginess-slider"), { target: { value: "5" } })
    expect(onChange).toHaveBeenCalledWith(5)
  })
})

describe("SceneSelector", () => {
  it("renders all 5 scene options", () => {
    render(<SceneSelector value={null} onChange={vi.fn()} />)
    for (const n of ["Techno", "Art", "Food", "Cocktails", "Nature"])
      expect(screen.getByText(n)).toBeInTheDocument()
  })

  it("fires onChange on click", () => {
    const onChange = vi.fn()
    render(<SceneSelector value={null} onChange={onChange} />)
    fireEvent.click(screen.getByText("Art"))
    expect(onChange).toHaveBeenCalledWith("art")
  })
})
