import { createElement } from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

// Override global framer-motion mock to add useReducedMotion
vi.mock("framer-motion", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

import { ChapterStepper } from "@/app/onboarding/components/chapter-stepper"
import { EdginessSlider } from "@/app/onboarding/components/edginess-slider"
import { SceneSelector } from "@/app/onboarding/components/scene-selector"

const chapters = [
  { number: 1, name: "Flirtation", tagline: "Break the ice", locked: false },
  { number: 2, name: "Infatuation", tagline: "Get closer", locked: false },
  { number: 3, name: "Attachment", tagline: "Build trust", locked: true },
  { number: 4, name: "Conflict", tagline: "Survive the storm", locked: true },
  { number: 5, name: "Commitment", tagline: "Prove yourself", locked: true },
]

describe("ChapterStepper", () => {
  it("renders all 5 chapters (desktop + mobile)", () => {
    render(<ChapterStepper currentChapter={1} chapters={chapters} />)
    expect(screen.getAllByRole("listitem")).toHaveLength(10) // 5 desktop + 5 mobile
  })

  it("marks current chapter with aria-current", () => {
    render(<ChapterStepper currentChapter={2} chapters={chapters} />)
    expect(screen.getAllByRole("listitem", { current: "step" })).toHaveLength(2)
  })

  it("displays chapter names", () => {
    render(<ChapterStepper currentChapter={1} chapters={chapters} />)
    expect(screen.getAllByText("Flirtation").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Commitment").length).toBeGreaterThan(0)
  })
})

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
