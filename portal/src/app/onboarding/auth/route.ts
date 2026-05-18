// Spec 216-H: /onboarding/auth route was deleted by Spec 216-G (PR #537).
// This explicit 410 GONE handler distinguishes "deletion shipped" from
// "auth gate caught it" (307 → /login) in monitoring + tests.
export const dynamic = "force-static"

export function GET() {
  return new Response("Gone", { status: 410 })
}

export function HEAD() {
  return new Response(null, { status: 410 })
}
