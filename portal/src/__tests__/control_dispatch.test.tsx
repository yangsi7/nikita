import { describe, expect, it } from "vitest"
import { useState } from "react"
import { render, screen } from "@testing-library/react"
import { TextInput } from "@/app/onboarding/_components/controls/TextInput"
import { Tel } from "@/app/onboarding/_components/controls/Tel"
import { CityInput } from "@/app/onboarding/_components/controls/CityInput"
import { Slider } from "@/app/onboarding/_components/controls/Slider"
import { Chips } from "@/app/onboarding/_components/controls/Chips"
import { Radio } from "@/app/onboarding/_components/controls/Radio"
import {
  Scenarios,
  SATURDAY_MORNING_OPTIONS,
} from "@/app/onboarding/_components/controls/Scenarios"
import { CombinedDualTextarea } from "@/app/onboarding/_components/controls/CombinedDualTextarea"

describe("control dispatch — AC C1.12 per-control ARIA", () => {
  it("TextInput has aria-required and aria-label", () => {
    render(
      <TextInput value="" onChange={() => {}} ariaLabel="your name" />
    )
    const inp = screen.getByLabelText(/your name/i)
    expect(inp).toHaveAttribute("aria-required", "true")
  })

  it("Tel has tel autocomplete + tel inputmode", () => {
    render(<Tel value="" onChange={() => {}} describedBy="why" />)
    const inp = screen.getByLabelText(/phone number/i)
    expect(inp).toHaveAttribute("autocomplete", "tel")
    expect(inp).toHaveAttribute("inputmode", "tel")
    expect(inp).toHaveAttribute("aria-describedby", "why")
  })

  it("Slider has aria-valuetext darkness ${value}/${max}", () => {
    render(<Slider value={7} onChange={() => {}} />)
    const slider = screen.getByLabelText(/darkness level/i)
    expect(slider).toHaveAttribute("aria-valuetext", "darkness 7/10")
  })

  it("CityInput renders the suggestion-chip group", () => {
    render(<CityInput value="" onChange={() => {}} />)
    expect(
      screen.getByRole("group", { name: /city suggestions/i })
    ).toBeInTheDocument()
  })

  it("Chips renders aria-pressed and a labelled group", () => {
    render(
      <Chips
        options={[
          { value: "a", label: "a" },
          { value: "b", label: "b" },
        ]}
        value="a"
        onChange={() => {}}
        ariaLabel="opts"
      />
    )
    const a = screen.getByRole("button", { name: "a" })
    expect(a).toHaveAttribute("aria-pressed", "true")
  })

  it("Radio renders an accessible radiogroup", () => {
    render(
      <Radio
        options={[
          { value: "x", label: "x" },
          { value: "y", label: "y" },
        ]}
        value={null}
        onChange={() => {}}
        ariaLabel="picks"
      />
    )
    expect(screen.getByRole("radiogroup", { name: /picks/i })).toBeInTheDocument()
  })

  it("Scenarios renders 3 radio cards", () => {
    render(
      <Scenarios
        options={SATURDAY_MORNING_OPTIONS}
        value={null}
        onChange={() => {}}
        ariaLabel="saturday morning"
      />
    )
    expect(screen.getAllByRole("radio")).toHaveLength(3)
  })

  it("CombinedDualTextarea wraps both fields in a fieldset legend (C1.18)", () => {
    function Harness() {
      const [t, setT] = useState("")
      const [o, setO] = useState("")
      return (
        <CombinedDualTextarea
          togetherValue={t}
          oddValue={o}
          onTogetherChange={setT}
          onOddChange={setO}
          helperId="helper"
        />
      )
    }
    render(<Harness />)
    expect(screen.getByLabelText(/what we'd do together/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/specific weird thing/i)).toBeInTheDocument()
  })
})
