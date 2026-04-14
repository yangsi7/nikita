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

// `path.resolve` anchors to the Next.js app root at runtime (process.cwd()
// on Vercel's serverless function). `outputFileTracingIncludes` in
// next.config.ts ensures these files are bundled into the deployment.
const ART_DIR = path.resolve("src/app/admin/systems/_art")

// Force-dynamic: every request goes through the admin middleware gate.
// No edge/CDN caching of authenticated content.
export const dynamic = "force-dynamic"

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
      // private + no-store prevents shared caches (Vercel Edge, proxies)
      // from retaining admin-gated content. Each request must re-fetch
      // and re-traverse middleware.
      "Cache-Control": "private, no-store, must-revalidate",
    },
  })
}
