import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MoodStrip } from "../mood-strip"

describe("MoodStrip — landing hero preview", () => {
  it("renders all 9 mood thumbnails", () => {
    const { container } = render(<MoodStrip />)
    const thumbs = container.querySelectorAll("img")
    expect(thumbs).toHaveLength(9)
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

  it("renders all 9 mood labels beneath thumbnails", () => {
    render(<MoodStrip />)
    for (const label of [
      "playful",
      "intimate",
      "excited",
      "cold",
      "angry",
      "stressed",
      "crying",
      "frustrated",
      "lustful",
    ]) {
      expect(screen.getByText(new RegExp(`^${label}$`, "i"))).toBeInTheDocument()
    }
  })

  it("includes lustful mood thumbnail", () => {
    render(<MoodStrip />)
    expect(screen.getByAltText("Nikita — lustful")).toBeInTheDocument()
  })

  it("li items have shrink-0 to prevent wrapping", () => {
    const { container } = render(<MoodStrip />)
    const items = container.querySelectorAll("li")
    expect(items.length).toBe(9)
    items.forEach((li) => {
      expect(li.className).toContain("shrink-0")
    })
  })
})
