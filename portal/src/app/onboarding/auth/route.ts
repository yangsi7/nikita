/**
 * Spec 216-H PR-E — explicit 410 GONE for the deleted `/onboarding/auth`
 * surface. The route was removed in #537 (Spec 216-G) when the
 * canonical signup flow flipped to TG-first. A 410 GONE response is
 * the correct intentional-sunset signal and lets monitoring + tests
 * distinguish "deletion shipped" from "auth gate caught it" (which is
 * what middleware would do without this handler — 307 to /login).
 *
 * The accompanying middleware passthrough lives in
 * `src/lib/supabase/middleware.ts`. The matching e2e assertion is in
 * `e2e/auth-flow.spec.ts`.
 */

const GONE_BODY =
  "This page has moved. Open Telegram and tap /start to begin signup."

export function GET(): Response {
  return new Response(GONE_BODY, {
    status: 410,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  })
}

export function POST(): Response {
  return new Response(GONE_BODY, {
    status: 410,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  })
}
