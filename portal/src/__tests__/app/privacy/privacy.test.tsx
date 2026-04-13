import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import PrivacyPage from "@/app/privacy/page"

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

describe("PrivacyPage", () => {
  it("renders the Privacy heading", () => {
    render(<PrivacyPage />)
    expect(screen.getByRole("heading", { name: "Privacy" })).toBeInTheDocument()
  })

  it("includes the mailto link for support@nikita.example", () => {
    render(<PrivacyPage />)
    const link = screen.getByRole("link", { name: "support@nikita.example" })
    expect(link).toHaveAttribute("href", "mailto:support@nikita.example")
  })

  it("includes a back link pointing to /onboarding", () => {
    render(<PrivacyPage />)
    const backLink = screen.getByRole("link", { name: /onboarding/i })
    expect(backLink).toHaveAttribute("href", "/onboarding")
  })
})
