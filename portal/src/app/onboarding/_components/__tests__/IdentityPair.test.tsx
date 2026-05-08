/**
 * Spec 217-3B AC-T-B.2 / AC-10b — IdentityPair compound control tests.
 *
 * Falsifier set:
 *   - full-valid render + submit → onSubmit called with both fields trimmed.
 *   - partial field_error rendering preserves typed value (AC-10b.3).
 *   - submit button disabled when age fails the digit-only client gate.
 */

import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { IdentityPair } from "../IdentityPair"

describe("IdentityPair", () => {
  it("submits trimmed name + age payload when both fields are filled", () => {
    const onSubmit = vi.fn()
    render(<IdentityPair onSubmit={onSubmit} />)
    fireEvent.change(screen.getByTestId("identity-pair-name"), {
      target: { value: "  Ada " },
    })
    fireEvent.change(screen.getByTestId("identity-pair-age"), {
      target: { value: " 28 " },
    })
    fireEvent.click(screen.getByTestId("identity-pair-submit"))
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith({ name: "Ada", age: "28" })
  })

  it("AC-10b.3: preserves entered name on partial field_error (age-only)", () => {
    const onSubmit = vi.fn()
    const { rerender } = render(
      <IdentityPair
        initialName="Ada"
        initialAge="17"
        onSubmit={onSubmit}
      />,
    )
    // Simulate the BE returning field_error{age: "must be 18+"} while the
    // valid name was persisted server-side. Caller re-renders with the
    // error map; the entered name MUST survive.
    rerender(
      <IdentityPair
        initialName="Ada"
        initialAge="17"
        fieldErrors={{ age: "must be 18 or older" }}
        onSubmit={onSubmit}
      />,
    )
    const nameInput = screen.getByTestId(
      "identity-pair-name",
    ) as HTMLInputElement
    expect(nameInput.value).toBe("Ada")
    const ageErr = screen.getByTestId("identity-pair-age-error")
    expect(ageErr.textContent).toBe("must be 18 or older")
    // The name field has NO error.
    expect(
      screen.queryByTestId("identity-pair-name-error"),
    ).toBeNull()
  })

  it("submit button is disabled until name is non-empty AND age is digits-only", () => {
    const onSubmit = vi.fn()
    render(<IdentityPair onSubmit={onSubmit} />)
    const submit = screen.getByTestId(
      "identity-pair-submit",
    ) as HTMLButtonElement
    expect(submit.disabled).toBe(true)
    fireEvent.change(screen.getByTestId("identity-pair-name"), {
      target: { value: "Ada" },
    })
    expect(submit.disabled).toBe(true)
    fireEvent.change(screen.getByTestId("identity-pair-age"), {
      target: { value: "twentyeight" },
    })
    expect(submit.disabled).toBe(true)
    fireEvent.change(screen.getByTestId("identity-pair-age"), {
      target: { value: "28" },
    })
    expect(submit.disabled).toBe(false)
  })
})
