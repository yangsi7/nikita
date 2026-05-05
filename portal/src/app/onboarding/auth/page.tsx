import type { Metadata } from "next"
import OnboardingAuthClient from "./page-client"

// Spec 214 PR #310 (entry-wiring): /onboarding/auth is step 2 of the
// 11-step cinematic onboarding wizard (FR-1). It is the Nikita-voiced
// magic-link request surface, reached via the landing-page CTA. After
// the user clicks the magic link in their inbox, /auth/confirm verifies
// the OTP (PKCE) and routes them to /onboarding (step 3+, wizard) via the
// `next=/onboarding` query parameter that this page passes to Supabase.
// EM-1 (plan §EM-1): unified callback at /auth/confirm; legacy
// /auth/callback shim was removed.
//
// Public route: middleware.ts allowlist already permits unauthenticated
// access (Spec 214 PR 214-C T312). Authenticated users hitting this URL
// are bounced to /dashboard or /admin by middleware before reaching this
// page.

export const metadata: Metadata = {
  title: "Access | Nikita",
  description: "Open the door.",
}

export default OnboardingAuthClient
