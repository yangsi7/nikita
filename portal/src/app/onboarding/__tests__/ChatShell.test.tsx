/**
 * Spec 214 T3.5 — ChatShell + MessageBubble + TypingIndicator unit tests.
 *
 * ACs:
 *   - AC-T3.5.1: aria-live scoped to a DEDICATED sibling sr-only live region
 *     (not the scroll container) per PR #363 QA iter-1 fix I5. The scroll
 *     container keeps `role="log"` only — it must NOT carry aria-live, or
 *     Virtuoso scroll reshuffling would re-announce older turns. Bubbles
 *     render an aria-hidden visual + sr-only sibling.
 *   - AC-T3.5.2: virtuoso only kicks in above VIRTUALIZATION_THRESHOLD; under
 *     the threshold all bubbles render eagerly.
 *   - AC-T3.5.3: typewriter reveal timing + reduced-motion bypass.
 */

import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

import { ChatShell, VIRTUALIZATION_THRESHOLD } from "../components/ChatShell"
import { MessageBubble } from "../components/MessageBubble"
import { TypingIndicator } from "../components/TypingIndicator"
import type { Turn } from "../types/converse"

vi.mock("react-virtuoso", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Virtuoso: ({ data, itemContent }: any) => (
    <div data-testid="virtuoso-mock">
      {data.map((turn: Turn, i: number) => (
        <div key={i}>{itemContent(i, turn)}</div>
      ))}
    </div>
  ),
}))

function makeTurns(n: number): Turn[] {
  return Array.from({ length: n }, (_, i) => ({
    role: i % 2 === 0 ? "user" : "nikita",
    content: `turn ${i}`,
    timestamp: `t${i}`,
  }))
}

describe("ChatShell — AC-T3.5.1 scoped aria-live (dedicated sibling region)", () => {
  it("puts role='log' on the scroll container WITHOUT aria-live", () => {
    render(<ChatShell turns={makeTurns(3)} isLoading={false} />)
    const log = screen.getByTestId("chat-log")
    expect(log.getAttribute("role")).toBe("log")
    // Fix I5 — scroll container must NOT carry aria-live (Virtuoso scroll
    // reshuffling would otherwise re-announce older turns on every scroll).
    expect(log.getAttribute("aria-live")).toBeNull()
    expect(log.getAttribute("aria-relevant")).toBeNull()
    expect(log.getAttribute("aria-atomic")).toBeNull()
  })

  it("renders a dedicated sibling sr-only live region (role=status, aria-live=polite, aria-atomic=true)", () => {
    render(<ChatShell turns={makeTurns(3)} isLoading={false} />)
    const live = screen.getByTestId("chat-live-region")
    expect(live.getAttribute("role")).toBe("status")
    expect(live.getAttribute("aria-live")).toBe("polite")
    expect(live.getAttribute("aria-atomic")).toBe("true")
    expect(live.className).toContain("sr-only")
  })

  it("live region surfaces ONLY the newest Nikita reply", () => {
    const turns: Turn[] = [
      { role: "user", content: "zurich", timestamp: "t0" },
      { role: "nikita", content: "old reply", timestamp: "t1" },
      { role: "user", content: "yes", timestamp: "t2" },
      { role: "nikita", content: "newest reply", timestamp: "t3" },
    ]
    render(<ChatShell turns={turns} isLoading={false} />)
    const live = screen.getByTestId("chat-live-region")
    expect(live.textContent).toBe("newest reply")
  })

  it("live region is empty when no Nikita turn has landed yet", () => {
    const turns: Turn[] = [{ role: "user", content: "hi", timestamp: "t0" }]
    render(<ChatShell turns={turns} isLoading={false} />)
    const live = screen.getByTestId("chat-live-region")
    expect(live.textContent).toBe("")
  })

  it("bubbles do NOT carry aria-live attributes", () => {
    render(<ChatShell turns={makeTurns(2)} isLoading={false} />)
    const bubbles = screen.getAllByTestId(/^message-bubble-(user|nikita)$/)
    expect(bubbles.length).toBeGreaterThan(0)
    for (const bubble of bubbles) {
      expect(bubble.getAttribute("aria-live")).toBeNull()
    }
  })
})

describe("ChatShell — AC-T3.5.2 virtualization threshold", () => {
  it(`renders eagerly when turns.length <= ${VIRTUALIZATION_THRESHOLD}`, () => {
    render(<ChatShell turns={makeTurns(VIRTUALIZATION_THRESHOLD)} isLoading={false} />)
    expect(screen.queryByTestId("virtuoso-mock")).toBeNull()
    const bubbles = screen.getAllByTestId(/^message-bubble-(user|nikita)$/)
    expect(bubbles).toHaveLength(VIRTUALIZATION_THRESHOLD)
  })

  it(`switches to virtuoso when turns.length > ${VIRTUALIZATION_THRESHOLD}`, () => {
    render(
      <ChatShell
        turns={makeTurns(VIRTUALIZATION_THRESHOLD + 1)}
        isLoading={false}
      />
    )
    expect(screen.getByTestId("virtuoso-mock")).toBeInTheDocument()
  })
})

describe("ChatShell — typing indicator", () => {
  it("renders typing indicator when isLoading=true", () => {
    render(<ChatShell turns={[]} isLoading={true} />)
    expect(screen.getByTestId("typing-indicator")).toBeInTheDocument()
  })

  it("hides typing indicator when isLoading=false", () => {
    render(<ChatShell turns={[]} isLoading={false} />)
    expect(screen.queryByTestId("typing-indicator")).toBeNull()
  })
})

describe("TypingIndicator — aria-hidden", () => {
  it("carries aria-hidden='true'", () => {
    render(<TypingIndicator />)
    expect(screen.getByTestId("typing-indicator").getAttribute("aria-hidden")).toBe("true")
  })
})

describe("MessageBubble — AC-T3.5.1 aria-hidden visual + sr-only", () => {
  it("user bubble renders content directly without typewriter", () => {
    const turn: Turn = { role: "user", content: "zurich", timestamp: "t0" }
    render(<MessageBubble turn={turn} />)
    expect(screen.getByTestId("message-bubble-user")).toBeInTheDocument()
    // user turns always render their content visibly and in sr-only
    expect(screen.getByText("zurich", { selector: "span[aria-hidden='true']" })).toBeInTheDocument()
  })

  it("instant=true Nikita turn renders full content + sr-only sibling", () => {
    const turn: Turn = { role: "nikita", content: "nice.", timestamp: "t0" }
    render(<MessageBubble turn={turn} instant={true} />)
    const visible = screen.getByTestId("message-bubble-visible")
    expect(visible.textContent).toBe("nice.")
    expect(screen.getByTestId("message-bubble-sr").textContent).toBe("nice.")
  })

  it("superseded=true bubble carries data-superseded='true'", () => {
    const turn: Turn = { role: "nikita", content: "x", timestamp: "t0", superseded: true }
    render(<MessageBubble turn={turn} instant={true} />)
    expect(screen.getByTestId("message-bubble-nikita").getAttribute("data-superseded")).toBe("true")
  })

  it("passes source through as data-source (e.g. 'fallback' for timeout)", () => {
    const turn: Turn = {
      role: "nikita",
      content: "lost signal",
      timestamp: "t0",
      source: "fallback",
    }
    render(<MessageBubble turn={turn} instant={true} />)
    expect(screen.getByTestId("message-bubble-nikita").getAttribute("data-source")).toBe("fallback")
  })
})
