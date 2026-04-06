import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MoodStrip } from "../mood-strip"

describe("MoodStrip — landing hero preview", () => {
  it("renders 4 mood thumbnails", () => {
    const { container } = render(<MoodStrip />)
    const thumbs = container.querySelectorAll("img")
    expect(thumbs).toHaveLength(4)
  })

  it("each thumbnail has a descriptive alt starting with 'Nikita'", () => {
    const { container } = render(<MoodStrip />)
    const thumbs = container.querySelectorAll("img")
    thumbs.forEach((img) => {
      expect(img.getAttribute("alt")).toMatch(/^Nikita — /)
    })
  })

  it("the list has an aria-label explaining intent", () => {
    const { container } = render(<MoodStrip />)
    const list = container.querySelector("ul")
    expect(list).toBeInTheDocument()
    expect(list?.getAttribute("aria-label")).toMatch(/mood range|not the same person/i)
  })

  it("renders mood labels beneath each thumbnail", () => {
    render(<MoodStrip />)
    expect(screen.getByText(/^playful$/i)).toBeInTheDocument()
    expect(screen.getByText(/^cold$/i)).toBeInTheDocument()
    expect(screen.getByText(/^intimate$/i)).toBeInTheDocument()
    expect(screen.getByText(/^angry$/i)).toBeInTheDocument()
  })
})
