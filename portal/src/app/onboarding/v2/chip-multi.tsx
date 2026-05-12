/**
 * Spec 218 Slice 218-4 — ChipMultiAsk shape renderer.
 *
 * Renders a set of toggle chips for multi-select. Each chip is a
 * Button with a pressed/unpressed visual state driven by a Set<string>
 * in local state. Submits the selected values as a string array.
 *
 * min_pick / max_pick from the envelope drive:
 *   - Submit button disabled until selection.size >= min_pick.
 *   - Chip toggle disabled once selection.size >= max_pick (prevents
 *     over-selection without removing a chip first).
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";

import type { ChipMultiAsk } from "./types/envelope";

type Props = {
  envelope: ChipMultiAsk;
  onSubmit: (values: string[]) => void;
};

export function ChipMultiShape({ envelope, onSubmit }: Props) {
  const [selected, setSelected] = React.useState<Set<string>>(new Set());

  const minPick = envelope.min_pick ?? 1;
  // FE hard cap mirrors server-side CHIP_MULTI_MAX_PICK=5
  // (nikita/agents/onboarding/v2/decorator_agent.py). Server validator
  // rejects ChipMultiAsk with max_pick > 5; FE enforces same ceiling
  // so an envelope missing max_pick can't surface over-cap selection.
  const CHIP_MULTI_MAX_PICK = 5;
  const maxPick = Math.min(envelope.max_pick ?? CHIP_MULTI_MAX_PICK, CHIP_MULTI_MAX_PICK);

  const toggle = (value: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) {
        next.delete(value);
      } else if (next.size < maxPick) {
        next.add(value);
      }
      return next;
    });
  };

  const canSubmit = selected.size >= minPick;

  return (
    <form
      data-testid="v2-chip-multi-shape"
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit([...selected]);
      }}
      className="flex flex-col gap-4"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>
      <div className="flex flex-wrap gap-2">
        {envelope.options.map((opt) => {
          const isSelected = selected.has(opt.value);
          const isDisabled =
            !isSelected && selected.size >= maxPick;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              disabled={isDisabled}
              aria-pressed={isSelected}
              className={[
                "rounded-full border px-3 py-1 text-sm transition-colors",
                isSelected
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-foreground border-border hover:bg-muted",
                isDisabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer",
              ].join(" ")}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
      <Button type="submit" disabled={!canSubmit} className="self-start">
        Next
      </Button>
    </form>
  );
}
