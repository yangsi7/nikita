import "@testing-library/jest-dom/vitest"
import { createElement } from "react"
import { vi } from "vitest"

// Global framer-motion mock — Proxy catches all motion.* element access
vi.mock("framer-motion", () => {
  const createMotionComponent = (tag: string) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const MotionComponent = ({ children, ...props }: any) => createElement(tag, props, children)
    MotionComponent.displayName = `motion.${tag}`
    return MotionComponent
  }
  const motion = new Proxy(
    {},
    {
      get: (_: object, tag: string) => createMotionComponent(tag),
    }
  )
  return {
    motion,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
    useScroll: () => ({ scrollY: { get: () => 0, onChange: vi.fn() } }),
    useTransform: (_: unknown, __: unknown, values: unknown[]) => values?.[0] ?? 0,
    useInView: () => true,
    useMotionValue: (v: unknown) => ({ get: () => v, set: vi.fn(), onChange: vi.fn() }),
    useSpring: (v: unknown) => ({ get: () => v, set: vi.fn() }),
  }
})

// Global `jest` shim so @testing-library/dom's `jestFakeTimersAreEnabled()`
// detects vitest fake timers. Without this shim, `waitFor` calls made while
// vi.useFakeTimers() is active hang — RTL's post-drain `setTimeout(resolve,0)`
// sits on the fake-timer queue and never fires because jest.advanceTimersByTime
// is missing. See:
//   node_modules/@testing-library/react/dist/pure.js asyncWrapper
//   node_modules/@testing-library/dom/dist/helpers.js jestFakeTimersAreEnabled
// This pattern is the canonical RTL+vitest fake-timer bridge documented in
// vitest's migration guide for jest users.
if (typeof (globalThis as { jest?: unknown }).jest === "undefined") {
  Object.defineProperty(globalThis, "jest", {
    configurable: true,
    writable: true,
    value: {
      advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms),
      runAllTimers: () => vi.runAllTimers(),
      useFakeTimers: () => vi.useFakeTimers(),
      useRealTimers: () => vi.useRealTimers(),
    },
  })
}

// Mock window.matchMedia for prefers-reduced-motion tests
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})
