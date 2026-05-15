/**
 * Spec 218 Slice 218-4 — ChipMultiAsk shape renderer.
 *
 * Renders a set of toggle chips for multi-select. Each chip is a
 * ToggleGroupItem with a pressed/unpressed visual state driven by a
 * Set<string> in local state. Submits the selected values as a string
 * array.
 *
 * min_pick / max_pick from the envelope drive:
 *   - Submit button disabled until selection.size >= min_pick.
 *   - Chip toggle disabled once selection.size >= max_pick (prevents
 *     over-selection without removing a chip first).
 *
 * Cluster X: replaced handroll <button> chips with shadcn ToggleGroup
 * (per components.json shadcn-primitive rule).
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

import type { ChipMultiAsk } from "./types/envelope";

type Props = {
  envelope: ChipMultiAsk;
  onSubmit: (values: string[]) => void;
};

export function ChipMultiShape({ envelope, onSubmit }: Props) {
  const [selected, setSelected] = React.useState<string[]>([]);

  // FE hard cap mirrors server-side CHIP_MULTI_MAX_PICK=5
  // (nikita/agents/onboarding/v2/decorator_agent.py). Server validator
  // rejects ChipMultiAsk with max_pick > 5; FE enforces same ceiling
  // so an envelope missing max_pick can't surface over-cap selection.
  const CHIP_MULTI_MAX_PICK = 5;
  const maxPick = Math.min(envelope.max_pick ?? CHIP_MULTI_MAX_PICK, CHIP_MULTI_MAX_PICK);
  // minPick clamped to maxPick so a buggy envelope with min_pick > maxPick
  // cannot strand the form in an unsubmittable state.
  const minPick = Math.min(envelope.min_pick ?? 1, maxPick);

  const canSubmit = selected.length >= minPick;

  const handleValueChange = (newValues: string[]) => {
    // Enforce maxPick — ToggleGroup type="multiple" allows any number
    if (newValues.length > maxPick) return;
    setSelected(newValues);
  };

  return (
    <form
      data-testid="v2-chip-multi-shape"
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit(selected);
      }}
      className="flex flex-col gap-4"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>
      <ToggleGroup
        type="multiple"
        value={selected}
        onValueChange={handleValueChange}
        className="flex flex-wrap gap-2 justify-start"
        variant="outline"
      >
        {envelope.options.map((opt) => {
          const isDisabled = !selected.includes(opt.value) && selected.length >= maxPick;
          return (
            <ToggleGroupItem
              key={opt.value}
              value={opt.value}
              disabled={isDisabled}
              aria-label={opt.label}
              className="rounded-full px-3 py-1 text-sm h-auto"
            >
              {opt.label}
            </ToggleGroupItem>
          );
        })}
      </ToggleGroup>
      <Button type="submit" disabled={!canSubmit} className="self-start">
        Continue
      </Button>
    </form>
  );
}
