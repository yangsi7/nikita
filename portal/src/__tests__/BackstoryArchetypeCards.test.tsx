import { useState } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { BackstoryArchetypeCards } from "@/app/onboarding/_components/BackstoryArchetypeCards"
import type { ArchetypeCard } from "@/app/onboarding/types/answer"

const VALID_CARDS: ArchetypeCard[] = [
  {
    label: "the runner",
    prose: "always moving, never quite arriving.",
    archetype_seed: "a".repeat(64),
  },
  {
    label: "the maker",
    prose: "hands always finishing something.",
    archetype_seed: "b".repeat(64),
  },
  {
    label: "the watcher",
    prose: "the corner of every room.",
    archetype_seed: "c".repeat(64),
  },
]

function Harness({ cards }: { cards: ArchetypeCard[] }) {
  const [picked, setPicked] = useState<string | null>(null)
  return (
    <BackstoryArchetypeCards
      cards={cards}
      selectedLabel={picked}
      onSelect={setPicked}
    />
  )
}

describe("BackstoryArchetypeCards — AC C1.7 / C1.12", () => {
  beforeEach(() => {
    vi.spyOn(console, "warn").mockImplementation(() => {})
  })

  it("renders a radiogroup with the documented label", () => {
    render(<Harness cards={VALID_CARDS} />)
    expect(
      screen.getByRole("radiogroup", { name: /pick a backstory/i })
    ).toBeInTheDocument()
  })

  it("renders all 3 cards as radio buttons", () => {
    render(<Harness cards={VALID_CARDS} />)
    const radios = screen.getAllByRole("radio")
    expect(radios).toHaveLength(3)
  })

  it("selecting a card flips aria-checked", () => {
    render(<Harness cards={VALID_CARDS} />)
    expect(
      screen.getByRole("radio", { name: /the runner/i })
    ).toHaveAttribute("aria-checked", "false")
    fireEvent.click(screen.getByRole("radio", { name: /the runner/i }))
    expect(
      screen.getByRole("radio", { name: /the runner/i })
    ).toHaveAttribute("aria-checked", "true")
  })

  it("warns and drops invalid archetype labels (12-list guard)", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
    const cards = [
      ...VALID_CARDS.slice(0, 2),
      {
        label: "the supreme leader" as never,
        prose: "invented label",
        archetype_seed: "d".repeat(64),
      } as ArchetypeCard,
    ]
    render(<Harness cards={cards} />)
    expect(screen.getAllByRole("radio")).toHaveLength(2)
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining("the supreme leader")
    )
  })
})
