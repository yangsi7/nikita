"use client"

/**
 * useReducedMotionCompat — vitest-mock-safe wrapper around
 * framer-motion's `useReducedMotion`.
 *
 * Two onboarding test files (DossierStamp, PipelineGate) re-mock
 * framer-motion with `useReducedMotion` exported. The global vitest mock
 * (`portal/vitest.setup.ts`) does not export it. Production framer-motion
 * always exports it.
 *
 * The `in` operator routes through the mock Proxy's `has` trap; vitest's
 * strict-mock Proxy only hooks `get`. So `"useReducedMotion" in FramerMotion`
 * is a safe, strict-check-free probe. We resolve the function reference
 * inside a try/catch as final belt-and-suspenders against future vitest
 * changes. When the hook is absent we fall back to a `matchMedia` probe.
 *
 * Shared across DossierStamp, PipelineGate, and StepShell so the
 * resolution logic has a single source of truth.
 */

import * as FramerMotion from "framer-motion"

type FramerReducedMotionHook = () => boolean | null

function resolveFramerReducedMotionHook(): FramerReducedMotionHook | null {
  try {
    if ("useReducedMotion" in FramerMotion) {
      const hook = (FramerMotion as { useReducedMotion?: unknown })
        .useReducedMotion
      if (typeof hook === "function") return hook as FramerReducedMotionHook
    }
  } catch {
    /* strict-mock proxy threw — fall through to null */
  }
  return null
}

const framerReducedMotionHook = resolveFramerReducedMotionHook()

export function useReducedMotionCompat(): boolean {
  if (framerReducedMotionHook !== null) {
    return !!framerReducedMotionHook()
  }
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}
