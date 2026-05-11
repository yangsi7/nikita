/**
 * Spec 218 Slice 218-2 — v2 envelope dispatcher (plan R14 + R2).
 *
 * Switch order:
 *   1. `envelope.handler === "v1"` -> mount v1 wizard handoff stub.
 *   2. `envelope.component` -> render the matching v2 shape component.
 *
 * Per plan R2: the dispatcher also surfaces `envelope.invalidated`
 * via the `onInvalidate` callback so the parent state machine can
 * clear stale local FE state for back-edited anchor slots.
 *
 * Slice 218-2 only ships the `text_short` shape + `handler_handoff`.
 * Slices 218-3..218-5 extend this switch with the remaining 6 shapes.
 */

"use client";

import * as React from "react";

import type { AskUnion } from "./types/envelope";
import { TextShortShape } from "./text-short";

type Props = {
  envelope: AskUnion;
  onSubmit: (value: unknown) => void;
  onInvalidate: (slots: string[]) => void;
};

export function DynamicQuestion({ envelope, onSubmit, onInvalidate }: Props) {
  // Plan R2: surface invalidated slots BEFORE rendering, so the parent
  // state machine clears stale local state in the same render cycle.
  // `invalidated` is read off the envelope as an optional extra field
  // because not every shape emits one.
  const invalidated = (
    envelope as unknown as { invalidated?: string[] }
  ).invalidated;
  React.useEffect(() => {
    if (invalidated && invalidated.length > 0) {
      onInvalidate(invalidated);
    }
  }, [invalidated, onInvalidate]);

  // Plan R14: handler check precedes component check. Defensive guard:
  // an envelope missing the `handler` field (malformed wire response,
  // version skew) defaults to `"v2"` because every v2-emitted shape
  // stamps `handler="v2"` at construction. Treating missing-handler as
  // v2 keeps the FE rendering the discriminated-component path rather
  // than falling through to the exhaustive `_exhaustive: never` check.
  const handler: "v1" | "v2" =
    (envelope as { handler?: "v1" | "v2" }).handler ?? "v2";
  if (handler === "v1") {
    return (
      <div
        data-testid="v1-handoff"
        data-next-url={
          envelope.component === "handler_handoff" ? envelope.next_url : ""
        }
      >
        {/*
          Slice 218-2: minimal handoff stub. Slice 218-3+ will replace
          this with a dynamic import of the legacy <ChatShell /> so the
          remainder of the session continues on the v1 path. For now
          the stub is enough to satisfy the dispatch contract + tests.
        */}
        <p className="text-sm text-muted-foreground">
          Continuing in legacy wizard...
        </p>
      </div>
    );
  }

  switch (envelope.component) {
    case "text_short":
      return (
        <TextShortShape
          envelope={envelope}
          onSubmit={(value) => onSubmit(value)}
        />
      );
    case "handler_handoff":
      // Defensive case: when `handler` field was missing AND component
      // is `handler_handoff`, the guard above defaulted handler to "v2"
      // and we land here. Render the same v1-handoff stub as the
      // handler-branched path so the user never sees a blank render.
      return (
        <div data-testid="v1-handoff" data-next-url={envelope.next_url}>
          <p className="text-sm text-muted-foreground">
            Continuing in legacy wizard...
          </p>
        </div>
      );
    case "text_long":
    case "single_select":
    case "chip_multi":
    case "slider":
    case "calendar":
    case "phone":
    case "complete":
      // Slices 218-3..218-5 add these branches. For slice 218-2, an
      // uncovered v2 component would be a route-handler bug (the BE
      // should have emitted handler_handoff). Render a defensive stub.
      return (
        <div data-testid="v2-component-not-implemented">
          <p className="text-sm text-destructive">
            Component {envelope.component} not yet implemented in this slice.
          </p>
        </div>
      );
    default: {
      const _exhaustive: never = envelope;
      return null;
    }
  }
}
