// Spec 220 PR-A: /login is no longer an active auth surface.
// Canonical entry point is the TG bot (?start=new) via middleware redirect.
// Return 410 Gone so crawlers and stale links fail loudly.
export async function GET() {
  return new Response(null, { status: 410, statusText: "Gone" })
}
