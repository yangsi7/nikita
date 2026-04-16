/**
 * WizardCopyAudit — static audit of the onboarding wizard sources.
 *
 * Spec 214 §855 calls out this test file as the guard that prevents
 * regressions against design-brief + Nikita-voiced-copy acceptance criteria.
 * It walks `portal/src/app/onboarding/steps/` and `portal/src/app/onboarding/components/`
 * with `node:fs` + regex and asserts:
 *
 *   - AC-1.5  Every step renders inside `StepShell` with a forwarded `testId`
 *             (so the wizard-step-N E2E selectors stay stable).
 *   - AC-2.2  `StepShell` pulls `FallingPattern` + `AuroraOrbs` from the
 *             landing primitive registry (no fork).
 *   - AC-2.3  No raw inline `style={{...}}` attributes except the documented
 *             `--bar-width` CSS-var exemption in `DossierHeader`.
 *   - AC-2.4  If a step uses `GlassCard`, it imports it from
 *             `@/components/landing/*` (no hand-rolled glass-card
 *             compositions).
 *   - AC-2.5  Every `<GlowButton …/>` instance has an `href` prop (CTA-link
 *             contract) or an explicit `asChild` wrapper.
 *   - AC-3.1  `copy.ts` contains none of the forbidden SaaS phrases listed
 *             in `docs/content/wizard-copy.md` §"Forbidden SaaS phrases".
 *   - AC-3.2  Every `cta: "…"` string literal in `copy.ts` has a matching
 *             entry in `docs/content/wizard-copy.md` (the canonical source
 *             of truth).
 */

import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

const ONBOARDING_DIR = join(__dirname, "..")
const STEPS_DIR = join(ONBOARDING_DIR, "steps")
const COMPONENTS_DIR = join(ONBOARDING_DIR, "components")
const WIZARD_COPY_MD = join(
  __dirname,
  "..",
  "..",
  "..",
  "..",
  "..",
  "docs",
  "content",
  "wizard-copy.md"
)

interface FileRecord {
  name: string
  path: string
  content: string
}

function readDir(dir: string, ext = ".tsx"): FileRecord[] {
  return readdirSync(dir)
    .filter((f) => f.endsWith(ext) && !f.includes(".test."))
    .map((name) => {
      const path = join(dir, name)
      return { name, path, content: readFileSync(path, "utf8") }
    })
}

describe("WizardCopyAudit — static source audit for Spec 214", () => {
  const stepFiles = readDir(STEPS_DIR)
  const componentFiles = readDir(COMPONENTS_DIR)

  describe("AC-1.5 — every step renders inside StepShell with testId", () => {
    it("each step file passes a testId to StepShell", () => {
      // DossierHeader IS a step (step 3), but it still flows through StepShell.
      for (const file of stepFiles) {
        if (file.name === "copy.ts" || file.name === "types.ts") continue
        expect(
          file.content,
          `${file.name}: expected to use <StepShell …> wrapper`
        ).toMatch(/<StepShell\b/)
        expect(
          file.content,
          `${file.name}: expected to pass testId= to StepShell`
        ).toMatch(/testId=/)
      }
    })
  })

  describe("AC-2.2 — StepShell sources FallingPattern + AuroraOrbs from landing primitives", () => {
    const stepShell = readFileSync(join(COMPONENTS_DIR, "StepShell.tsx"), "utf8")

    it("imports FallingPattern from landing/", () => {
      expect(stepShell).toMatch(
        /from\s+["']@\/components\/landing\/falling-pattern["']/
      )
    })

    it("imports AuroraOrbs from landing/", () => {
      expect(stepShell).toMatch(
        /from\s+["']@\/components\/landing\/aurora-orbs["']/
      )
    })
  })

  describe("AC-2.3 — no inline style attributes (with whitelist)", () => {
    // Allowed patterns — documented exemptions with rationale.
    const ALLOWED_INLINE_STYLE_PATTERNS: RegExp[] = [
      // DossierHeader metric bars route dynamic width through a CSS custom
      // property; Tailwind cannot express geometry driven by runtime values
      // without an arbitrary-value class per render, which tailwind's JIT
      // cannot precompute. This is the documented exemption per spec §AC-2.3.
      /style=\{\{\s*["']--bar-width["']\s*:/,
    ]

    it("step + component .tsx files have no raw inline style except whitelisted CSS-var patterns", () => {
      const allFiles = [...stepFiles, ...componentFiles]
      for (const file of allFiles) {
        // Strip comments before scanning — AC-2.3 only forbids inline styles
        // in RENDERED output, not in documentation prose that happens to
        // reference `style={{…}}` in comments.
        // Order matters: strip JSX comments first so the embedded /* */ does
        // not leak back into the TS-comment pass.
        const sanitized = file.content
          .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")   // JSX comments {/* … */}
          .replace(/\/\*[\s\S]*?\*\//g, "")         // block comments /* … */
          .replace(/\/\/.*$/gm, "")                  // line comments // …
        // Match style={{ ... }} — non-greedy, stops at the first }}.
        const styleRegex = /style=\{\{[^}]*\}\}/g
        const matches = sanitized.match(styleRegex) ?? []
        for (const match of matches) {
          const allowed = ALLOWED_INLINE_STYLE_PATTERNS.some((p) => p.test(match))
          expect(
            allowed,
            `${file.name}: unexpected inline style '${match}' (not in whitelist)`
          ).toBe(true)
        }
      }
    })
  })

  describe("AC-2.4 — GlassCard imported from landing/, not re-implemented", () => {
    it("any step/component that uses GlassCard imports it from @/components/landing/", () => {
      for (const file of [...stepFiles, ...componentFiles]) {
        if (!file.content.includes("GlassCard")) continue
        expect(
          file.content,
          `${file.name}: uses <GlassCard> but does not import from @/components/landing/`
        ).toMatch(/from\s+["']@\/components\/landing\//)
      }
    })
  })

  describe("AC-2.5 — GlowButton used as href CTA, not onClick", () => {
    it("every GlowButton usage has href= or asChild (link contract)", () => {
      const glowButtonOpenTagRegex = /<GlowButton\b[^>]*>/g
      for (const file of [...stepFiles, ...componentFiles]) {
        const matches = file.content.match(glowButtonOpenTagRegex) ?? []
        for (const match of matches) {
          const hasHref = match.includes("href=")
          const hasAsChild = match.includes("asChild")
          expect(
            hasHref || hasAsChild,
            `${file.name}: GlowButton '${match}' has neither href= nor asChild — not a link CTA`
          ).toBe(true)
        }
      }
    })
  })

  describe("AC-3.1 — no SaaS rejection-list copy in copy.ts", () => {
    const FORBIDDEN_PHRASES: readonly string[] = [
      "Continue",
      "Continue.",
      "Get Started",
      "Sign Up",
      "Submit",
      "Next step",
      "Next.",
      "Processing...",
      "Loading...",
      "Success",
    ]

    it("copy.ts contains no forbidden SaaS phrases", () => {
      const raw = readFileSync(join(STEPS_DIR, "copy.ts"), "utf8")
      // Strip block + line comments so docstring prose can reference
      // forbidden words without triggering a false positive.
      const code = raw
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/\/\/.*$/gm, "")

      for (const phrase of FORBIDDEN_PHRASES) {
        // Escape regex metacharacters.
        const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
        const re = new RegExp(`["']${escaped}["']`)
        expect(
          code,
          `copy.ts contains forbidden phrase "${phrase}" — Nikita-voiced copy required`
        ).not.toMatch(re)
      }
    })
  })

  describe("AC-3.2 — copy.ts CTA strings are mirrored in wizard-copy.md", () => {
    it("every cta: \"…\" literal in copy.ts also appears verbatim in wizard-copy.md", () => {
      const copyContent = readFileSync(join(STEPS_DIR, "copy.ts"), "utf8")
      const wizardCopyMd = readFileSync(WIZARD_COPY_MD, "utf8")

      // Collect every string literal that follows a key ending in "cta"
      // (cta, ctaCards, ctaDegraded, ctaVoice, ctaText, ...).
      const ctaRegex = /\b\w*[Cc][Tt][Aa]\w*\s*:\s*["']([^"']+)["']/g
      const ctaValues = new Set<string>()
      let m: RegExpExecArray | null
      while ((m = ctaRegex.exec(copyContent)) !== null) {
        ctaValues.add(m[1])
      }

      expect(ctaValues.size, "copy.ts must export at least one CTA string").toBeGreaterThan(0)

      for (const cta of ctaValues) {
        expect(
          wizardCopyMd,
          `wizard-copy.md is missing CTA string "${cta}" — copy.ts and docs must stay in sync (Spec 214 FR-3, AC-3.2)`
        ).toContain(cta)
      }
    })
  })
})
