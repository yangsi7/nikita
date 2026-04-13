/**
 * Research Lab model manifest.
 *
 * Each entry describes a behavior model in the Nikita system. Add entries
 * here to surface new models in the Research Lab dashboard without any
 * routing changes.
 */

export type ModelStatus = "active" | "experimental" | "deprecated"
export type ModelCategory = "timing" | "scoring" | "memory" | "personalization" | "other"

export interface ModelEntry {
  /** URL-safe identifier used in /admin/research-lab/[slug] */
  slug: string
  /** Human-readable display name */
  title: string
  /** Lifecycle status */
  status: ModelStatus
  /** Functional category for grouping */
  category: ModelCategory
  /** One-line description shown on the index card */
  summary: string
  /**
   * Relative path from repo root to the interactive HTML artifact.
   * When present, rendered as a sandboxed iframe on the detail page.
   * The portal prebuild script syncs matching files to portal/public/research-lab/.
   */
  artifactPath?: string
  /**
   * Relative path from repo root to the long-form markdown documentation.
   * Read at request time via fs.readFile and rendered with react-markdown + remark-gfm.
   */
  markdownPath?: string
  /** Repo-relative path to the primary implementation file, shown as a GitHub link */
  codeRef?: string
  /** Repo-relative path to the feature spec, shown as a GitHub link */
  specRef?: string
  /** ISO date string — displayed in card footer and detail header */
  updatedAt: string
}

export const MODELS: ModelEntry[] = [
  {
    slug: "response-timing",
    title: "Response Timing Model",
    status: "active",
    category: "timing",
    summary:
      "Log-normal × chapter-coefficient delay with per-chapter hard caps and EWMA momentum layer. Nikita's reply cadence adapts to the user's own messaging rhythm.",
    artifactPath: "/research-lab/response-timing-explorer.html",
    markdownPath: "docs/models/response-timing.md",
    codeRef: "nikita/agents/text/timing.py",
    specRef: "specs/210-kill-skip-variable-response/spec.md",
    updatedAt: "2026-04-13",
  },
  {
    slug: "nikita-overview",
    title: "Nikita: Don't Get Dumped — System Overview",
    status: "active",
    category: "other",
    summary:
      "Complete reference for how Nikita works: relationship scoring, chapter progression, boss encounters, decay mechanics, and vice personalization.",
    markdownPath: "docs/how-nikita-works.md",
    updatedAt: "2026-04-13",
  },
]

/** Ordered list of category labels for grouping on the index page */
export const CATEGORY_ORDER: ModelCategory[] = [
  "timing",
  "scoring",
  "memory",
  "personalization",
  "other",
]

export const CATEGORY_LABELS: Record<ModelCategory, string> = {
  timing: "Timing",
  scoring: "Scoring",
  memory: "Memory",
  personalization: "Personalization",
  other: "Other",
}

export const STATUS_VARIANTS: Record<ModelStatus, "default" | "secondary" | "destructive" | "outline"> = {
  active: "default",
  experimental: "secondary",
  deprecated: "outline",
}
