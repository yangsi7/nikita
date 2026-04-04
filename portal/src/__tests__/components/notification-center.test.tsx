/**
 * Tests for NotificationCenter component
 * Verifies notification list, mark-read, empty state, unread badge
 */
import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NotificationCenter } from "@/components/notifications/notification-center"
import type { PortalNotification } from "@/lib/api/types"

// Radix ScrollArea needs ResizeObserver
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
})

const mockNotifications: PortalNotification[] = [
  {
    id: "n1",
    type: "chapter_advance",
    title: "Chapter Advanced!",
    message: "You've reached Chapter 3",
    timestamp: "2026-03-20T12:00:00Z",
    read: false,
    actionHref: "/dashboard",
  },
  {
    id: "n2",
    type: "decay_warning",
    title: "Score Decaying!",
    message: "Your score is dropping fast",
    timestamp: "2026-03-20T11:00:00Z",
    read: true,
  },
]

const mockMarkAsRead = vi.fn()
const mockMarkAllAsRead = vi.fn()

vi.mock("@/hooks/use-notifications", () => ({
  useNotifications: () => ({
    notifications: mockNotifications,
    unreadCount: 1,
    markAsRead: mockMarkAsRead,
    markAllAsRead: mockMarkAllAsRead,
  }),
}))

describe("NotificationCenter", () => {
  it("renders notification bell button", () => {
    render(<NotificationCenter />)
    expect(screen.getByRole("button", { name: /notifications/i })).toBeInTheDocument()
  })

  it("shows unread count badge", () => {
    render(<NotificationCenter />)
    expect(screen.getByText("1")).toBeInTheDocument()
  })

  it("opens popover with notification list on click", async () => {
    const user = userEvent.setup()
    render(<NotificationCenter />)

    await user.click(screen.getByRole("button", { name: /notifications/i }))

    expect(screen.getByText("Chapter Advanced!")).toBeInTheDocument()
    expect(screen.getByText("You've reached Chapter 3")).toBeInTheDocument()
    expect(screen.getByText("Score Decaying!")).toBeInTheDocument()
  })

  it("shows 'Mark all read' button when unread exist", async () => {
    const user = userEvent.setup()
    render(<NotificationCenter />)

    await user.click(screen.getByRole("button", { name: /notifications/i }))

    expect(screen.getByText("Mark all read")).toBeInTheDocument()
  })

  it("calls markAllAsRead when 'Mark all read' is clicked", async () => {
    const user = userEvent.setup()
    render(<NotificationCenter />)

    await user.click(screen.getByRole("button", { name: /notifications/i }))
    await user.click(screen.getByText("Mark all read"))

    expect(mockMarkAllAsRead).toHaveBeenCalled()
  })

  it("calls markAsRead when a notification is clicked", async () => {
    const user = userEvent.setup()
    render(<NotificationCenter />)

    await user.click(screen.getByRole("button", { name: /notifications/i }))
    await user.click(screen.getByText("Chapter Advanced!"))

    expect(mockMarkAsRead).toHaveBeenCalledWith("n1")
  })
})
