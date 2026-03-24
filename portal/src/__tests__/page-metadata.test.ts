/**
 * Validates that every portal page exports Next.js metadata
 * with a title (containing " | Nikita" or "Nikita") and a non-empty description.
 *
 * Spec 169 — Portal Page Metadata
 */
import { describe, it, expect } from "vitest"

/**
 * All portal pages that must export metadata.
 * Root page.tsx is excluded because it is a redirect-only page.
 */
const PAGES_WITH_METADATA: { path: string; importPath: string }[] = [
  { path: "login", importPath: "@/app/login/page" },
  { path: "onboarding", importPath: "@/app/onboarding/page" },
  { path: "dashboard", importPath: "@/app/dashboard/page" },
  { path: "dashboard/conversations", importPath: "@/app/dashboard/conversations/page" },
  { path: "dashboard/conversations/[id]", importPath: "@/app/dashboard/conversations/[id]/page" },
  { path: "dashboard/diary", importPath: "@/app/dashboard/diary/page" },
  { path: "dashboard/engagement", importPath: "@/app/dashboard/engagement/page" },
  { path: "dashboard/insights", importPath: "@/app/dashboard/insights/page" },
  { path: "dashboard/nikita", importPath: "@/app/dashboard/nikita/page" },
  { path: "dashboard/nikita/circle", importPath: "@/app/dashboard/nikita/circle/page" },
  { path: "dashboard/nikita/day", importPath: "@/app/dashboard/nikita/day/page" },
  { path: "dashboard/nikita/mind", importPath: "@/app/dashboard/nikita/mind/page" },
  { path: "dashboard/nikita/stories", importPath: "@/app/dashboard/nikita/stories/page" },
  { path: "dashboard/settings", importPath: "@/app/dashboard/settings/page" },
  { path: "dashboard/vices", importPath: "@/app/dashboard/vices/page" },
  { path: "admin", importPath: "@/app/admin/page" },
  { path: "admin/conversations/[id]", importPath: "@/app/admin/conversations/[id]/page" },
  { path: "admin/jobs", importPath: "@/app/admin/jobs/page" },
  { path: "admin/pipeline", importPath: "@/app/admin/pipeline/page" },
  { path: "admin/prompts", importPath: "@/app/admin/prompts/page" },
  { path: "admin/text", importPath: "@/app/admin/text/page" },
  { path: "admin/users", importPath: "@/app/admin/users/page" },
  { path: "admin/users/[id]", importPath: "@/app/admin/users/[id]/page" },
  { path: "admin/voice", importPath: "@/app/admin/voice/page" },
]

describe("Page metadata exports", () => {
  it.each(PAGES_WITH_METADATA)(
    "$path exports metadata with title and description",
    async ({ importPath }) => {
      // Dynamic import to load the page module
      const mod = await import(/* @vite-ignore */ importPath)

      expect(mod.metadata).toBeDefined()
      expect(typeof mod.metadata.title).toBe("string")
      expect(mod.metadata.title).toContain("Nikita")
      expect(typeof mod.metadata.description).toBe("string")
      expect(mod.metadata.description.length).toBeGreaterThan(0)
    },
  )

  it("covers all 24 non-redirect pages", () => {
    expect(PAGES_WITH_METADATA).toHaveLength(24)
  })
})
