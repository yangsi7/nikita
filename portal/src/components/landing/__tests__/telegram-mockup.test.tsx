import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TelegramMockup } from "../telegram-mockup"

describe("TelegramMockup — T015 AC-REQ-010", () => {
  it("renders all 7 message bubbles in extended conversation", () => {
    const { container } = render(<TelegramMockup />)
    const bubbles = container.querySelectorAll("[data-testid='message-bubble']")
    expect(bubbles).toHaveLength(7)
  })

  it("renders extended conversation: character + memory + warmth", () => {
    render(<TelegramMockup />)
    // Opening: recall of user's stress
    expect(screen.getByText(/meeting you were stressed about/i)).toBeInTheDocument()
    // User's disbelief
    expect(screen.getByText(/how do you remember that/i)).toBeInTheDocument()
    // Memory callback — specific detail
    expect(screen.getByText(/last tuesday.*11pm|new director scared you/i)).toBeInTheDocument()
    // Character line
    expect(screen.getByText(/i listen\. try it sometime/i)).toBeInTheDocument()
    // Closing warmth — flirt hint
    expect(screen.getByText(/proud of you\. don't make it weird/i)).toBeInTheDocument()
  })

  it("header shows 'online' status (she's alive)", () => {
    render(<TelegramMockup />)
    expect(screen.getByText(/^online$/i)).toBeInTheDocument()
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
