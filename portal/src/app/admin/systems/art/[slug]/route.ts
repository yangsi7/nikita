import { NextResponse } from "next/server"

import { ART_HTML } from "../../_art-generated"

/**
 * Admin-gated art dispatcher. Serves the five vendored generative-art
 * showcases from the auto-generated ART_HTML record. Every request runs
 * through admin middleware (route is under /admin/*).
 *
 * HTML content is compiled into the serverless bundle at build time via
 * scripts/generate-art-module.mjs — no runtime filesystem access, no
 * deployment-tracing concerns.
 */

const ALLOWED = new Set([
  "fluid-dynamics",
  "physarum-slime-mold",
  "ecosystem",
  "double-pendulum-chaos",
  "fractal-flames",
])

// Force-dynamic ensures middleware runs on every request — no edge/CDN
// caching of authenticated content.
export const dynamic = "force-dynamic"

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params

  // Next.js URL-decodes dynamic route segments before passing them here,
  // so the allowlist rejects any "../" / "%2e%2e" attempt before the
  // ART_HTML lookup runs. Only the 5 literal names pass.
  if (!ALLOWED.has(slug)) {
    return new NextResponse("Not Found", { status: 404 })
  }

  const html = ART_HTML[slug]
  if (html === undefined) {
    // Belt-and-suspenders: ALLOWED is in sync with the codegen output,
    // but if the generator skipped a file we 404 rather than 500.
    return new NextResponse("Not Found", { status: 404 })
  }

  return new NextResponse(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      // Defence-in-depth: the iframe carries sandbox="allow-scripts", but
      // opening the URL standalone loads the HTML in a full tab context
      // where the CSP sandbox keyword provides the same boundary.
      "Content-Security-Policy": "sandbox allow-scripts",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      // private + no-store prevents shared caches (Vercel Edge, proxies)
      // from retaining admin-gated content. must-revalidate is redundant
      // with no-store so omitted.
      "Cache-Control": "private, no-store",
    },
  })
}
