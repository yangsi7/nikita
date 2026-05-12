/**
 * Spec 218 Slice 218-7 — PhoneDemoModal + PhoneDemoTakeover (FR-009/FR-010)
 *
 * RED phase: components stub raise; tests verify structure and imports compile.
 * GREEN phase: stubs replaced with real implementation; behaviour tests pass.
 *
 * AC coverage:
 *   AC-001: PhoneDemoModal renders with skip and consent actions
 *   AC-002: PhoneDemoModal default focus is on Skip (FR-009 default-skip)
 *   AC-003: PhoneDemoTakeover has aria-live region with correct text (FR-010)
 *   AC-004: alert-dialog component compiles without import errors
 */

import { describe, it, expect, vi } from "vitest"

describe("PhoneDemoModal (Spec 218 Slice 218-7 - RED)", () => {
  it("AC-004: alert-dialog component exports compile", async () => {
    // Verify the shadcn alert-dialog component is importable — will fail
    // if @radix-ui/react-alert-dialog is missing or alert-dialog.tsx has errors.
    const mod = await import("@/components/ui/alert-dialog")
    expect(mod.AlertDialog).toBeDefined()
    expect(mod.AlertDialogContent).toBeDefined()
    expect(mod.AlertDialogTitle).toBeDefined()
    expect(mod.AlertDialogDescription).toBeDefined()
    expect(mod.AlertDialogFooter).toBeDefined()
    expect(mod.AlertDialogHeader).toBeDefined()
    expect(mod.AlertDialogAction).toBeDefined()
    expect(mod.AlertDialogCancel).toBeDefined()
  })

  it("AC-001 (RED): PhoneDemoModal module exports PhoneDemoModal function", async () => {
    // In RED phase, the import should succeed (component file exists)
    // but calling render will throw NotImplementedError from the stub.
    const mod = await import("@/app/onboarding/v2/phone_demo_modal")
    expect(typeof mod.PhoneDemoModal).toBe("function")
  })

  it("AC-003 (RED): PhoneDemoTakeover module exports PhoneDemoTakeover function", async () => {
    const mod = await import("@/app/onboarding/v2/phone_demo_takeover")
    expect(typeof mod.PhoneDemoTakeover).toBe("function")
  })

  it("AC-002 (RED): PhoneDemoModal throws stub error on render (GREEN phase needed)", async () => {
    // This verifies the stub IS a stub — it should throw.
    // GREEN phase replaces the throw with real JSX.
    const { PhoneDemoModal } = await import("@/app/onboarding/v2/phone_demo_modal")
    const noop = vi.fn()
    expect(() =>
      PhoneDemoModal({ open: true, onSkip: noop, onConsent: noop })
    ).toThrow("PhoneDemoModal — GREEN phase not implemented")
  })
})
