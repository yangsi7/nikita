/**
 * Tests for DashboardEmptyState component
 * Verifies empty state renders correctly for onboarded-but-never-chatted users
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { DashboardEmptyState } from "@/components/dashboard/dashboard-empty-state"

describe("DashboardEmptyState", () => {
  it("renders the welcome heading", () => {
    render(<DashboardEmptyState />)
    expect(
      screen.getByText("Welcome to Nikita's World")
    ).toBeInTheDocument()
  })

  it("renders a Telegram link with the correct URL", () => {
    render(<DashboardEmptyState />)
    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link).toHaveAttribute("href", "https://t.me/Nikita_my_bot")
  })

  it("opens the Telegram link in a new tab", () => {
    render(<DashboardEmptyState />)
    const link = screen.getByRole("link", { name: /chat on telegram/i })
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
  })

  it("has data-testid attribute for testing", () => {
    render(<DashboardEmptyState />)
    expect(screen.getByTestId("dashboard-empty-state")).toBeInTheDocument()
  })

  it("renders the body text", () => {
    render(<DashboardEmptyState />)
    expect(
      screen.getByText(/start chatting with nikita on telegram/i)
    ).toBeInTheDocument()
  })
})
