import { readFile } from "node:fs/promises"
import path from "node:path"
import { NextResponse } from "next/server"

/**
 * Admin-gated art dispatcher. Serves the five vendored generative-art
 * showcases from `portal/src/app/admin/systems/_art/` after the admin
 * middleware gate has fired (the route sits under /admin/*).
 *
 * Rationale: Next.js `public/*` assets are served by the static file
 * layer and cannot be reliably auth-gated via middleware (Vercel CDN
 * runs before Edge Middleware for static paths). Routing the HTML
 * through a Route Handler under /admin/systems/* guarantees the admin
 * check runs for every request — including deep-links to standalone
 * view.
 */

const ALLOWED = new Set([
  "fluid-dynamics",
  "physarum-slime-mold",
  "ecosystem",
  "double-pendulum-chaos",
  "fractal-flames",
])

const ART_DIR = path.join(
  process.cwd(),
  "src",
  "app",
  "admin",
  "systems",
  "_art",
)

export const dynamic = "force-static"

export async function generateStaticParams() {
  return [...ALLOWED].map((slug) => ({ slug }))
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params

  if (!ALLOWED.has(slug)) {
    return new NextResponse("Not Found", { status: 404 })
  }

  const html = await readFile(path.join(ART_DIR, `${slug}.html`), "utf-8")

  return new NextResponse(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      // Defence-in-depth: the iframe tag already carries sandbox="allow-scripts",
      // but an admin clicking "Open standalone" loads the HTML in a full tab
      // context where the CSP sandbox keyword provides the same boundary.
      "Content-Security-Policy": "sandbox allow-scripts",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "Cache-Control": "public, max-age=3600, must-revalidate",
    },
  })
}
