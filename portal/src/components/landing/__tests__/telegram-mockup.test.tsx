import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TelegramMockup } from "../telegram-mockup"

describe("TelegramMockup — T015 AC-REQ-010", () => {
  it("renders all 3 message bubbles", () => {
    const { container } = render(<TelegramMockup />)
    const bubbles = container.querySelectorAll("[data-testid='message-bubble']")
    expect(bubbles).toHaveLength(3)
  })

  it("renders the exact 3 messages from spec", () => {
    render(<TelegramMockup />)
    // Message 1 (her): did you just leave me on read
    expect(screen.getByText(/left me on read/i)).toBeInTheDocument()
    // Message 2 (you): sorry i was busy
    expect(screen.getByText(/sorry.*busy|busy.*sorry/i)).toBeInTheDocument()
    // Message 3 (her): sure you were
    expect(screen.getByText(/sure you were/i)).toBeInTheDocument()
  })

  it("her messages visually distinct from you messages", () => {
    const { container } = render(<TelegramMockup />)
    const herMessages = container.querySelectorAll("[data-sender='her']")
    const youMessages = container.querySelectorAll("[data-sender='you']")
    expect(herMessages.length).toBeGreaterThan(0)
    expect(youMessages.length).toBeGreaterThan(0)
    // Her messages and you messages should have different styling
    const herClass = herMessages[0].className
    const youClass = youMessages[0].className
    expect(herClass).not.toBe(youClass)
  })

  it("wrapped in a glass card or accessible container", () => {
    const { container } = render(<TelegramMockup />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toBeInTheDocument()
    // Should have glass styling
    expect(wrapper.className).toMatch(/glass|bg-white\/|backdrop/)
  })
})
