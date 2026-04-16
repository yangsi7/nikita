/**
 * Onboarding loading fallback (Spec 214 PR 214-C, T313).
 *
 * Nikita-voiced copy per spec FR-3 (zero-SaaS-copy rule). The dossier
 * skeleton mirrors the wizard's classified-file header so users don't
 * see a context switch between initial paint and wizard mount.
 *
 * Copy is inlined here until PR 214-B lands `docs/content/wizard-copy.md`
 * (T233) as the canonical reference. The phrasing below is sourced
 * directly from spec §FR-3 step-copy examples.
 */

export default function OnboardingLoading() {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-void-ambient px-6"
      role="status"
      aria-live="polite"
    >
      <div className="flex w-full max-w-md flex-col items-center gap-8">
        {/* Classified-file title band — mirrors DossierHeader typography */}
        <div className="w-full space-y-3 text-center">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground">
            CLASSIFIED / FILE-ACCESS
          </p>
          <h1 className="text-[clamp(2rem,5vw,3.5rem)] font-black leading-none tracking-tighter">
            ACCESSING FILE...
          </h1>
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-muted-foreground/80">
            She&apos;s pulling your dossier.
          </p>
        </div>

        {/* Dossier skeleton — 4 placeholder rows suggesting the wizard shape */}
        <div className="w-full space-y-3">
          <div className="h-4 w-1/3 animate-pulse rounded-sm bg-muted-foreground/20" />
          <div className="h-10 w-full animate-pulse rounded-sm bg-muted-foreground/15" />
          <div className="h-4 w-1/4 animate-pulse rounded-sm bg-muted-foreground/20" />
          <div className="h-10 w-full animate-pulse rounded-sm bg-muted-foreground/15" />
        </div>

        {/* Spinner — single accent dot with roseglow hue */}
        <div className="size-3 animate-pulse rounded-full bg-primary/80" aria-hidden />
        <span className="sr-only">Loading Nikita&apos;s dossier on you.</span>
      </div>
    </div>
  )
}
