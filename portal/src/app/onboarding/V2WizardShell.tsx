"use client";

import * as React from "react";
import { env } from "@/lib/env";
import { DynamicQuestion } from "./v2/DynamicQuestion";
import type { AskUnion } from "./v2/types/envelope";

/**
 * Spec 218 Slice 218-8 — minimal v2 wizard shell.
 *
 * Bootstraps the onboarding conversation:
 * 1. POSTs to /api/v1/converse/onboarding (no body for first-turn).
 * 2. Renders the envelope returned via DynamicQuestion.
 * 3. On submit: POSTs the slot value, gets next envelope, re-renders.
 * 4. Loops until envelope.component === "complete".
 *
 * No legacy v1 chat shell, no WizardPersistence (server is single
 * source of truth per ADR-009). Uses env.API_URL (fail-fast module,
 * Spec 216-EM3a) instead of bare process.env.NEXT_PUBLIC_API_URL.
 */
export function V2WizardShell() {
  const [envelope, setEnvelope] = React.useState<AskUnion | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const fetchTurn = React.useCallback(
    async (body: { slot_kind?: string; value?: unknown } | null) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          env.API_URL + "/api/v1/converse/onboarding",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
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
    [],
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
    return (
      <div
        className="flex h-screen items-center justify-center"
        data-testid="v2-complete"
      >
        <p>Onboarding complete!</p>
      </div>
    );
  }
  return (
    <div className="flex h-screen items-center justify-center p-8">
      <DynamicQuestion
        envelope={envelope}
        onSubmit={(value) => {
          if ("slot" in envelope) {
            fetchTurn({ slot_kind: envelope.slot, value });
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
