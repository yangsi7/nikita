import "@testing-library/jest-dom/vitest"
import { createElement } from "react"
import { vi } from "vitest"

// Spec 216 EM-2: stub the public Telegram bot username for components
// that read `env.TELEGRAM_BOT_USERNAME` (e.g. ClearanceGrantedCeremony).
// `process.env.NODE_ENV === "test"` already prevents env.ts from
// throwing on missing vars, but consumers still read the empty string;
// stub a sensible default so suites that assert on the resolved URL
// don't have to set it themselves. Suites that DO want to test
// missing-env behaviour can use `vi.stubEnv(...)` per-test.
if (!process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME) {
  process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME = "Nikita_my_bot"
}

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
    // Default false. Tests that need to exercise the reduced-motion branch
    // override per-file via vi.mock() at the top of the test:
    //
    //   vi.mock("framer-motion", async () => {
    //     const actual = await vi.importActual<typeof import("framer-motion")>("framer-motion")
    //     return { ...actual, useReducedMotion: () => true }
    //   })
    //
    // The global default mirrors a browser without `prefers-reduced-motion:
    // reduce`, so most tests render the full-motion branch.
    useReducedMotion: () => false,
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
