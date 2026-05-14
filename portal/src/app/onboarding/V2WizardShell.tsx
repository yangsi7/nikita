"use client";

import * as React from "react";
import { env } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";
import { DynamicQuestion } from "./v2/DynamicQuestion";
import type { AskUnion } from "./v2/types/envelope";

/**
 * Spec 218 Slice 218-8 — minimal v2 wizard shell.
 *
 * Bootstraps the onboarding conversation:
 * 1. Reads access_token from the browser Supabase session.
 * 2. POSTs to /api/v1/onboarding/answer with Authorization: Bearer <jwt>
 *    (no body for first-turn).
 * 3. Renders the envelope returned via DynamicQuestion.
 * 4. On submit: POSTs the slot value, gets next envelope, re-renders.
 * 5. Loops until envelope.component === "complete".
 *
 * Auth contract (GH #594, Walk Final 2026-05-13):
 *   Backend route is gated by Depends(get_authenticated_user) which
 *   reads `Authorization: Bearer <jwt>`. `credentials: include` (cookie
 *   path) is not honored by the backend; the JWT MUST travel as a
 *   Bearer header. The session is sourced from `createBrowserClient`
 *   (single supabase-js source-of-truth, same client used by the
 *   wider portal). If the session is missing (logged-out tab, expired
 *   cookie), we surface "not authenticated" instead of firing the
 *   401-bound fetch — clearer error boundary copy + zero noise in
 *   backend logs.
 *
 * No legacy v1 chat shell, no WizardPersistence (server is single
 * source of truth per ADR-009). Uses env.API_URL (fail-fast module,
 * Spec 216-EM3a) instead of bare process.env.NEXT_PUBLIC_API_URL.
 */
export function V2WizardShell() {
  const [envelope, setEnvelope] = React.useState<AskUnion | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  // Memoize the Supabase browser client — `createBrowserClient` returns
  // a fresh instance per call, and we want one for the lifetime of this
  // component.
  const supabase = React.useMemo(() => createClient(), []);

  const fetchTurn = React.useCallback(
    async (body: { slot_kind?: string; value?: unknown } | null) => {
      setLoading(true);
      setError(null);
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) {
          throw new Error("not authenticated");
        }
        const res = await fetch(
          env.API_URL + "/api/v1/onboarding/answer",
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            // No `credentials: "include"` — backend gates on Bearer
            // header only; sending cross-origin cookies would expand the
            // CSRF attack surface for no functional benefit.
            body: JSON.stringify(body ?? {}),
          },
        );
        if (!res.ok) {
          throw new Error("HTTP " + res.status);
        }
        const data = await res.json();
        setEnvelope(data as AskUnion);
      } catch (err) {
        setError(err instanceof Error ? err.message : "unknown");
      } finally {
        setLoading(false);
      }
    },
    [supabase],
  );

  React.useEffect(() => {
    fetchTurn(null);
  }, [fetchTurn]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Loading&hellip;
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex h-screen items-center justify-center text-destructive">
        Error: {error}
      </div>
    );
  }
  if (!envelope) return null;
  if (envelope.component === "complete") {
    return <CompleteRedirect envelope={envelope} />;
  }
  return (
    <div className="flex h-screen items-center justify-center p-8">
      <DynamicQuestion
        envelope={envelope}
        onSubmit={(value) => {
          if ("slot" in envelope) {
            // Phase-2 turns carry slot="phase2_followup" in the envelope so
            // DynamicQuestion has a stable discriminator key, but the backend
            // V2AnswerRequest.slot_kind must be null for Phase-2 (SlotKindV2
            // enum intentionally excludes "phase2_followup" — free-text exchange,
            // no deterministic slot to write). GH #606 fix (2026-05-14).
            // Phase-2 turns carry slot="phase2_followup" in the envelope so
            // DynamicQuestion has a stable discriminator key, but the backend
            // V2AnswerRequest.slot_kind must be omitted (undefined) for Phase-2
            // so Pydantic serialises it as null/None and enum validation passes.
            // SlotKindV2 intentionally excludes "phase2_followup". GH #606.
            const slotKind =
              envelope.slot === "phase2_followup" ? undefined : envelope.slot;
            fetchTurn({ slot_kind: slotKind, value });
          } else {
            // Defensive: envelope without slot is a server contract violation
            // (only CompleteAsk has no slot, and it returns early above).
            // Surface as error rather than silent no-op so misconfigured
            // server state doesn't strand the user.
            setError(
              `received envelope without slot field (component=${(envelope as { component: string }).component})`,
            );
          }
        }}
        onInvalidate={() => {
          /* slice 218-8: invalidated slots tracked server-side; FE
             refetches next envelope on submit so no local action. */
        }}
      />
    </div>
  );
}


/**
 * Same-origin path guard. Accepts only single-leading-slash paths
 * whose second character is NOT `/`, `\`, or any whitespace (tab,
 * newline, space, etc. — some browsers normalize these as host
 * delimiters during URL parsing). Anything else — protocol-relative,
 * absolute URL, `javascript:`, `data:`, whitespace-prefixed host —
 * is rejected.
 *
 * Implementation: a single regex `^\/[^/\\\s]` over the trailing
 * `length > 1` check covers `/`, `\`, and all Unicode whitespace
 * without the prefix-by-prefix enumeration that allowed `/\t...` to
 * slip past. Exported for unit tests; the type guard return narrows
 * the caller to `string`.
 */
const SAFE_PATH_RE = /^\/[^/\\\s]/;

export function isSameOriginPath(raw: unknown): raw is string {
  if (typeof raw !== "string") return false;
  // Allow the bare-slash root path `/` (regex requires a second
  // non-delimiter char and would reject it).
  if (raw === "/") return true;
  return SAFE_PATH_RE.test(raw);
}

function CompleteRedirect({ envelope }: { envelope: AskUnion }) {
  // useEffect-driven redirect avoids side-effect-in-render (StrictMode
  // double-invoke safe). Hard window.location navigation invalidates
  // wizard-local cache.
  //
  // Same-origin guard: a malicious/malformed `next_route` (e.g.
  // `javascript:...`, `https://evil.com`, `//evil.com`, or
  // `/\evil.com` — browsers normalize `\` to `/` for the host
  // delimiter, so `/\evil.com` resolves cross-origin) would otherwise
  // execute via `window.location.href`. Accept only paths that begin
  // with a single forward slash and do NOT continue with either `/`
  // or `\`; fall back to /dashboard otherwise.
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    // CompleteAsk declares `next_route: string` (envelope.ts:104),
    // but a server contract violation could ship `undefined` past
    // Pydantic in extreme cases. `isSameOriginPath` is a type guard
    // that narrows non-string to false, so the runtime fallback to
    // `/dashboard` is safe even if the static type lies.
    const raw =
      envelope.component === "complete" ? envelope.next_route : undefined;
    const safeTarget = isSameOriginPath(raw) ? raw : "/dashboard";
    window.location.href = safeTarget;
  }, [envelope]);

  return (
    <div
      className="flex h-screen items-center justify-center"
      data-testid="v2-complete"
    >
      <p>Onboarding complete! Redirecting…</p>
    </div>
  );
}
