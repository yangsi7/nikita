# Plan — Subspec 217-1 Cold-Start CTA + Interstitial + Loading Flash

**Parent**: `subspecs/217-1-cold-start-cta-interstitial/spec.md`
**Phase**: 5
**Date**: 2026-05-07

## Architecture

FE-only sub-PR. Three independent edits sharing one branch + one PR (coupled by Walk B1 verification).

### URL append (FR-1)

Use the standard `URLSearchParams` API. Pattern:

```ts
const url = new URL(`https://t.me/${env.TELEGRAM_BOT_USERNAME}`);
url.searchParams.set("start", "welcome");
const ctaHref = url.toString();
```

This survives any pre-existing UTM tags or tracking params on the href.

### Interstitial reskin (FR-2)

UA-default-safe inversion: brand-veil ALWAYS renders; auto-advance is the LAYER that requires positive UA detection.

```tsx
// InterstitialClient.tsx (sketch)
"use client";
export function InterstitialClient({ next, ua }: Props) {
  const router = useRouter();
  useEffect(() => { router.prefetch(next); }, [next, router]);
  useEffect(() => {
    if (ua.confirmedNonIosNonIab) {
      // schedule programmatic advance after a short brand-veil flash
      const t = setTimeout(() => router.push(next), 100);
      return () => clearTimeout(t);
    }
  }, [ua, next, router]);
  return (
    <BrandVeil>
      <AuroraOrbs />
      <h1 className="font-geist-sans">tap to enter</h1>
      <GlowButton onClick={() => router.push(next)}>tap to enter</GlowButton>
    </BrandVeil>
  );
}
```

UA detection lives server-side in `page.tsx` via `userAgent()` from `next/server` so SSR + client agree.

### Loading flash (FR-3)

Step-1: identify source via Chrome MCP DevTools trace. Suspects (per ERRATA): `loading.tsx`, `PipelineGate.tsx:69-73`, `WizardShell.tsx:773`. The 216-C wizard does NOT mount PipelineGate (per spike artifact); so candidates narrow to `loading.tsx` (Next.js suspense fallback) + a possible WizardShell pre-data render.

Step-2: replace whichever surface flashes "in development / in progress" with:
- shadcn/ui `Skeleton` matching the wizard card silhouette
- Spec 208 brand veil background

## Verification

- Walk B1 (12-step) per `live-testing-protocol.md` from `simon.yang.ch+walkB1@gmail.com`.
- Playwright UA fixture for the 3 UA cases.
- Performance API budget assertion (warm + cold).
- Pre-push gate + zero-tolerance `/qa-review`.

## Risks

| Risk | Mitigation |
|---|---|
| `URLSearchParams` import path differs across files | Stick to `new URL(...)` constructor (browser-native, no import) |
| iOS standalone PWA UA detection false-negative on UA shifts | Default-safe degrades to brand-veil + tap (correct fallback) |
| Skeleton silhouette doesn't match wizard card → visible jump | Match dimensions to actual `WizardShell` Card outer dims |

## Dependencies

217-0 merged.
