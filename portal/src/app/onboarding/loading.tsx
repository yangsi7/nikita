export default function OnboardingLoading() {
  return (
    <div className="flex h-screen items-center justify-center bg-void">
      <div className="flex flex-col items-center gap-4">
        <div className="size-8 animate-spin rounded-full border-2 border-muted-foreground border-t-primary" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  )
}
