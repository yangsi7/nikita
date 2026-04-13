import { describe, it, expect } from "vitest"
import fs from "fs"
import path from "path"
import {
  MODELS,
  CATEGORY_ORDER,
  CATEGORY_LABELS,
  STATUS_VARIANTS,
  type ModelEntry,
  type ModelStatus,
  type ModelCategory,
} from "@/app/admin/research-lab/models"

// From tests/research-lab/ → tests/ → portal/ → worktree root (repo root)
const REPO_ROOT = path.join(__dirname, "../../..")

describe("Research Lab models manifest", () => {
  it("has at least one model entry", () => {
    expect(MODELS.length).toBeGreaterThan(0)
  })

  it("contains the response-timing model", () => {
    const rt = MODELS.find((m) => m.slug === "response-timing")
    expect(rt).toBeDefined()
  })

  it("contains the nikita-overview model", () => {
    const ov = MODELS.find((m) => m.slug === "nikita-overview")
    expect(ov).toBeDefined()
  })

  describe("every entry has required fields", () => {
    MODELS.forEach((model: ModelEntry) => {
      it(`model '${model.slug}' has all required fields`, () => {
        expect(model.slug).toBeTruthy()
        expect(model.title).toBeTruthy()
        expect(model.status).toMatch(/^(active|experimental|deprecated)$/)
        expect(model.category).toMatch(/^(timing|scoring|memory|personalization|other)$/)
        expect(model.summary).toBeTruthy()
        expect(model.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      })
    })
  })

  it("slugs are unique", () => {
    const slugs = MODELS.map((m) => m.slug)
    const uniqueSlugs = new Set(slugs)
    expect(uniqueSlugs.size).toBe(slugs.length)
  })

  it("slugs are URL-safe (no spaces, lowercase)", () => {
    for (const model of MODELS) {
      expect(model.slug).toMatch(/^[a-z0-9-]+$/)
    }
  })

  describe("referenced markdownPath files exist", () => {
    MODELS.filter((m) => m.markdownPath).forEach((model: ModelEntry) => {
      it(`markdownPath for '${model.slug}' exists on disk`, () => {
        const fullPath = path.join(REPO_ROOT, model.markdownPath!)
        expect(fs.existsSync(fullPath), `Expected file at ${fullPath}`).toBe(true)
      })
    })
  })

  describe("STATUS_VARIANTS covers all statuses", () => {
    const statuses: ModelStatus[] = ["active", "experimental", "deprecated"]
    statuses.forEach((s) => {
      it(`STATUS_VARIANTS has entry for '${s}'`, () => {
        expect(STATUS_VARIANTS[s]).toBeDefined()
      })
    })
  })

  describe("CATEGORY_LABELS covers all categories", () => {
    const categories: ModelCategory[] = ["timing", "scoring", "memory", "personalization", "other"]
    categories.forEach((c) => {
      it(`CATEGORY_LABELS has entry for '${c}'`, () => {
        expect(CATEGORY_LABELS[c]).toBeTruthy()
      })
    })
  })

  it("CATEGORY_ORDER contains all categories exactly once", () => {
    const categories: ModelCategory[] = ["timing", "scoring", "memory", "personalization", "other"]
    expect(CATEGORY_ORDER.sort()).toEqual(categories.sort())
  })

  it("response-timing has correct artifactPath, codeRef, and specRef", () => {
    const rt = MODELS.find((m) => m.slug === "response-timing")!
    expect(rt.artifactPath).toBe("/research-lab/response-timing-explorer.html")
    expect(rt.codeRef).toBe("nikita/agents/text/timing.py")
    expect(rt.specRef).toBe("specs/210-kill-skip-variable-response/spec.md")
  })

  it("nikita-overview has no artifactPath (markdown-only model)", () => {
    const ov = MODELS.find((m) => m.slug === "nikita-overview")!
    expect(ov.artifactPath).toBeUndefined()
    expect(ov.markdownPath).toBe("docs/how-nikita-works.md")
  })
})
