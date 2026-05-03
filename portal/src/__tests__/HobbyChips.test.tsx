import { useState } from "react"
import { describe, expect, it } from "vitest"
import { fireEvent, render, screen, within } from "@testing-library/react"
import {
  HobbyChips,
  hobbyPicksValid,
  serializeHobbies,
} from "@/app/onboarding/_components/HobbyChips"
import { HOBBY_CATEGORIES } from "@/app/onboarding/_components/hobby-taxonomy"

function Harness({
  initialPicks = [],
  initialOther = "",
}: {
  initialPicks?: string[]
  initialOther?: string
}) {
  const [picks, setPicks] = useState<string[]>(initialPicks)
  const [other, setOther] = useState<string>(initialOther)
  return (
    <HobbyChips
      picks={picks}
      other={other}
      onPicksChange={(next) => setPicks([...next])}
      onOtherChange={setOther}
    />
  )
}

describe("HobbyChips — AC C1.6", () => {
  it("renders ARIA group with the documented label", () => {
    render(<Harness />)
    expect(
      screen.getByRole("group", { name: /primary hobbies/i })
    ).toBeInTheDocument()
  })

  it("groups chips by all 10 categories", () => {
    render(<Harness />)
    for (const cat of HOBBY_CATEGORIES) {
      expect(
        screen.getByRole("heading", { name: new RegExp(cat, "i") })
      ).toBeInTheDocument()
    }
  })

  it("filters chips via the autocomplete combobox", () => {
    render(<Harness />)
    const combo = screen.getByRole("combobox")
    fireEvent.change(combo, { target: { value: "techn" } })
    // Music's `techno` chip survives, others vanish.
    expect(
      screen.getByRole("button", { name: /^techno$/i })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /^running$/i })
    ).not.toBeInTheDocument()
  })

  it("toggles picks via aria-pressed", () => {
    render(<Harness />)
    expect(
      screen.getByRole("button", { name: /^techno$/i })
    ).toHaveAttribute("aria-pressed", "false")
    fireEvent.click(screen.getByRole("button", { name: /^techno$/i }))
    expect(
      screen.getByRole("button", { name: /^techno$/i })
    ).toHaveAttribute("aria-pressed", "true")
  })

  it("blocks a sixth pick (caps at 5)", () => {
    render(<Harness />)
    const labels = ["techno", "jazz", "indie rock", "classical", "hip-hop"]
    for (const l of labels) {
      fireEvent.click(screen.getByRole("button", { name: new RegExp(`^${l}$`, "i") }))
    }
    const reggae = screen.getByRole("button", { name: /^reggae$/i })
    fireEvent.click(reggae)
    expect(reggae).toHaveAttribute("aria-pressed", "false")
  })

  it("announces count via live region", () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole("button", { name: /^techno$/i }))
    expect(screen.getByText(/1\/5 picked/i)).toBeInTheDocument()
  })

  it("'+ other' helper turns rose at len ≥35", () => {
    render(<Harness />)
    const other = screen.getByPlaceholderText(/something not above/i)
    fireEvent.change(other, {
      target: { value: "x".repeat(35) },
    })
    expect(screen.getByText(/35\/40/)).toBeInTheDocument()
  })

  it("'+ other' caps at 40 chars via maxLength", () => {
    render(<Harness />)
    const other = screen.getByPlaceholderText(
      /something not above/i
    ) as HTMLInputElement
    expect(other.maxLength).toBe(40)
  })

  it("hobbyPicksValid: 3-5 inclusive", () => {
    expect(hobbyPicksValid([], "")).toBe(false)
    expect(hobbyPicksValid(["a", "b"], "")).toBe(false)
    expect(hobbyPicksValid(["a", "b", "c"], "")).toBe(true)
    expect(hobbyPicksValid(["a", "b", "c", "d", "e"], "")).toBe(true)
    expect(hobbyPicksValid(["a", "b", "c", "d", "e", "f"], "")).toBe(false)
  })

  it("hobbyPicksValid counts non-empty trimmed other as one pick", () => {
    expect(hobbyPicksValid(["a", "b"], "  ")).toBe(false)
    expect(hobbyPicksValid(["a", "b"], "knitting")).toBe(true)
  })

  it("serializeHobbies trims + comma-joins picks + other", () => {
    expect(serializeHobbies(["techno", "jazz"], "  knitting  ")).toBe(
      "techno, jazz, knitting"
    )
    expect(serializeHobbies(["techno"], "")).toBe("techno")
  })
})

describe("HobbyChips smoke", () => {
  it("renders inside the documented group landmark", () => {
    render(<Harness />)
    const group = screen.getByRole("group", { name: /primary hobbies/i })
    // chip count is a sanity floor; exact taxonomy size = 100.
    const buttons = within(group).getAllByRole("button")
    expect(buttons.length).toBeGreaterThanOrEqual(100)
  })
})
