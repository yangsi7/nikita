/**
 * Spec 218 Slice 218-2/218-3/218-4/218-5/218-8 — v2 envelope dispatcher.
 *
 * Switch order: `envelope.component` -> render the matching v2 shape component.
 *
 * Per plan R2: the dispatcher also surfaces `envelope.invalidated`
 * via the `onInvalidate` callback so the parent state machine can
 * clear stale local FE state for back-edited anchor slots.
 *
 * PR-218-8: HandlerHandoffAsk + v1 handler branch removed (all 11 Phase-1
 * slots are now covered by v2).
 *
 * Cluster X: added BlurFade entrance animation; removed dead `complete`
 * case (intercepted by V2WizardShell before reaching this component).
 */

"use client";

import * as React from "react";

import { BlurFade } from "@/components/ui/blur-fade";
import type { AskUnion } from "./types/envelope";
import { CalendarShape } from "./calendar";
import { ChipMultiShape } from "./chip-multi";
import { PhoneShape } from "./phone";
import { SingleSelectShape } from "./single-select";
import { SliderShape } from "./slider";
import { TextLongShape } from "./text-long";
import { TextShortShape } from "./text-short";


type Props = {
  envelope: AskUnion;
  onSubmit: (value: unknown) => void;
  onInvalidate: (slots: string[]) => void;
};

export function DynamicQuestion({ envelope, onSubmit, onInvalidate }: Props) {
  // Plan R2: surface invalidated slots BEFORE rendering, so the parent
  // state machine clears stale local state in the same render cycle.
  const rawInvalidated = (
    envelope as unknown as { invalidated?: string[] }
  ).invalidated;
  const invalidatedKey = React.useMemo(
    () => (rawInvalidated && rawInvalidated.length > 0
      ? [...rawInvalidated].sort().join(",")
      : ""),
    [rawInvalidated],
  );
  React.useEffect(() => {
    if (invalidatedKey) {
      onInvalidate(invalidatedKey.split(","));
    }
  }, [invalidatedKey, onInvalidate]);

  // Key the BlurFade on the slot so each slot transition triggers
  // the entrance animation fresh.
  const slotKey = "slot" in envelope ? envelope.slot : envelope.component;

  const inner = (() => {
    switch (envelope.component) {
      case "text_short":
        return (
          <TextShortShape
            envelope={envelope}
            onSubmit={(value) => onSubmit(value)}
          />
        );
      case "calendar":
        return (
          <CalendarShape
            envelope={envelope}
            onSubmit={(isoDate) => onSubmit(isoDate)}
          />
        );
      case "single_select":
        return (
          <SingleSelectShape
            envelope={envelope}
            onSubmit={(optionValue) => onSubmit(optionValue)}
          />
        );
      case "chip_multi":
        return (
          <ChipMultiShape
            envelope={envelope}
            onSubmit={(values) => onSubmit(values)}
          />
        );
      case "phone":
        return (
          <PhoneShape
            envelope={envelope}
            onSubmit={(value) => onSubmit(value)}
          />
        );
      case "slider":
        return (
          <SliderShape
            envelope={envelope}
            onSubmit={(value) => onSubmit(value)}
          />
        );
      case "text_long":
        return (
          <TextLongShape
            envelope={envelope}
            onSubmit={(value) => onSubmit(value)}
          />
        );
      case "complete":
        // Dead code path — CompleteAsk is intercepted by V2WizardShell
        // before DynamicQuestion is rendered. Kept for exhaustiveness.
        return null;
      default: {
        const _exhaustive: never = envelope;
        return null;
      }
    }
  })();

  if (!inner) return null;

  return (
    <BlurFade
      key={slotKey}
      delay={0}
      duration={0.15}
      blur="6px"
      offset={8}
      direction="up"
    >
      {inner}
    </BlurFade>
  );
}
