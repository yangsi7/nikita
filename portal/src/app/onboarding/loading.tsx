import { Skeleton } from "@/components/ui/skeleton"

/**
 * Onboarding loading fallback — Spec 217-1 FR-3 / AC-3.2 / AC-3.4.
 *
 * Spec 208 brand veil (bg-void) + shadcn `Skeleton` rows matching the
 * wizard chat-card silhouette. Replaces the Spec 214 PR 214-C "NIKITA IS
 * COMING..." placeholder copy that flashed between magic-link click and
 * the first wizard frame (user-reported regression #3).
 *
 * Visual budget: brand veil renders the same surface the wizard mounts
 * onto, so the suspense → mount transition is a content-only swap (no
 * background color flash). Skeleton dimensions mirror WizardShell's
 * QuestionCard outer dims so the silhouette doesn't visibly jump.
 *
 * NO chatty placeholder copy ("in development" / "in progress" / "NIKITA
 * IS COMING..." etc.) — the brand veil + silhouette are sufficient
 * affordance, and chatty copy was the documented flash source.
 *
 * a11y: role=status + aria-live=polite preserved for screen readers; an
 * sr-only label provides the accessible name without leaking copy to the
 * visual layer.
 */
export default function OnboardingLoading() {
  return (
    <div
      className="flex min-h-screen w-full items-center justify-center overflow-hidden bg-void px-6"
      role="status"
      aria-live="polite"
    >
      <div className="flex w-full max-w-md flex-col items-center gap-6">
        {/* Card silhouette — matches WizardShell QuestionCard outer dims. */}
        <Skeleton className="h-3 w-1/3 rounded-full bg-white/10" />
        <Skeleton className="h-12 w-full rounded-md bg-white/10" />
        <Skeleton className="h-3 w-1/2 rounded-full bg-white/10" />
        <Skeleton className="h-32 w-full rounded-md bg-white/10" />
        <Skeleton className="h-10 w-2/3 rounded-md bg-white/10" />
      </div>
      <span className="sr-only">Loading.</span>
    </div>
  )
}
