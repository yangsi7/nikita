/**
 * Onboarding layout — bg-void + aurora-orbs ambient layer.
 *
 * Wraps all /onboarding/** pages in the landing-parity dark background
 * with animated orbs. Children render above the ambient layer via z-10.
 *
 * V2WizardShell adds its own bg-void wrapper for inner pages where it
 * controls the full viewport; this layout provides the fallback for
 * auth/ and loading.tsx which don't have their own background.
 */

import { AuroraOrbs } from "@/components/landing/aurora-orbs";

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen bg-void bg-void-ambient">
      <AuroraOrbs />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
