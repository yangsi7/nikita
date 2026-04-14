import { readFile } from "node:fs/promises"
import path from "node:path"
import { NextResponse } from "next/server"

/**
 * Admin-gated art dispatcher. Serves the five vendored generative-art
 * showcases from `portal/src/app/admin/systems/_art/` after the admin
 * middleware gate has fired (the route sits under /admin/*).
 *
 * MUST be dynamic (force-dynamic) — SSG/force-static would pre-render
 * the response at build time and Vercel CDN would serve it without
 * running middleware on cache hits, defeating the admin gate.
 */

const ALLOWED = new Set([
  "fluid-dynamics",
  "physarum-slime-mold",
  "ecosystem",
  "double-pendulum-chaos",
  "fractal-flames",
])

// Anchored to the Next.js app root at runtime (process.cwd()). On Vercel
// serverless functions, cwd is /var/task — the function bundle root.
// `outputFileTracingIncludes` in next.config.ts copies the _art/*.html
// files into the bundle at this same relative path.
const ART_DIR = path.join(
  process.cwd(),
  "src",
  "app",
  "admin",
  "systems",
  "_art",
)

// Module-scoped cache. HTML files are immutable post-deploy, so a cold-start
// read followed by in-memory hits eliminates redundant disk I/O when a user
// lands on /admin/systems (5 iframes × request for 5 slugs).
const htmlCache = new Map<string, string>()

async function loadHtml(slug: string): Promise<string | null> {
  const cached = htmlCache.get(slug)
  if (cached !== undefined) return cached

  try {
    const html = await readFile(path.join(ART_DIR, `${slug}.html`), "utf-8")
    htmlCache.set(slug, html)
    return html
  } catch (err) {
    console.error(
      `[admin/systems/art] failed to read ${slug}.html from ${ART_DIR}:`,
      err,
    )
    return null
  }
}

// Force-dynamic: every request goes through the admin middleware gate.
// No edge/CDN caching of authenticated content.
export const dynamic = "force-dynamic"

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params

  // Allowlist runs on the URL-decoded slug (Next.js decodes route segments
  // before passing them in). Only literal matches against the 5 known names
  // pass; any "../" / "%2e%2e" attempt gets rejected here before any
  // filesystem interaction.
  if (!ALLOWED.has(slug)) {
    return new NextResponse("Not Found", { status: 404 })
  }

  const html = await loadHtml(slug)
  if (html === null) {
    // File missing on disk (deploy bundle gap or stale ALLOWED set).
    // Return 404 with a plain body — do not leak Node error stack to clients.
    return new NextResponse("Not Found", { status: 404 })
  }

  return new NextResponse(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      // Defence-in-depth: the iframe tag already carries sandbox="allow-scripts",
      // but an admin clicking "Open standalone" loads the HTML in a full tab
      // context where the CSP sandbox keyword provides the same boundary.
      "Content-Security-Policy": "sandbox allow-scripts",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      // private + no-store prevents shared caches (Vercel Edge, proxies)
      // from retaining admin-gated content. Each request must re-fetch
      // and re-traverse middleware.
      "Cache-Control": "private, no-store, must-revalidate",
    },
  })
}
