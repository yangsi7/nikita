/**
 * Spec 218 Slice 218-3 — SingleSelectAsk shape renderer.
 *
 * Renders a shadcn RadioGroup + Button bound to the envelope's slot,
 * prompt, and options. Submits the selected Option.value string.
 *
 * The Radix RadioGroupPrimitive Item carries `value` (the canonical
 * machine-readable string the BE persists) while the visible Label
 * shows `option.label` (and optional `blurb`).
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

import type { SingleSelectAsk } from "./types/envelope";

type Props = {
  envelope: SingleSelectAsk;
  onSubmit: (optionValue: string) => void;
};

export function SingleSelectShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");

  return (
    <form
      data-testid="v2-single-select-shape"
      onSubmit={(e) => {
        e.preventDefault();
        if (!value) return;
        onSubmit(value);
      }}
      className="flex flex-col gap-4"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>
      <RadioGroup
        value={value}
        onValueChange={setValue}
        aria-label={envelope.prompt}
      >
        {envelope.options.map((opt) => (
          <div key={opt.value} className="flex items-start gap-3">
            <RadioGroupItem
              id={`v2-${envelope.slot}-${opt.value}`}
              value={opt.value}
            />
            <div className="flex flex-col">
              <Label
                htmlFor={`v2-${envelope.slot}-${opt.value}`}
                className="cursor-pointer"
              >
                {opt.label}
              </Label>
              {opt.blurb ? (
                <span className="text-sm text-muted-foreground">
                  {opt.blurb}
                </span>
              ) : null}
            </div>
          </div>
        ))}
      </RadioGroup>
      <Button type="submit" disabled={!value} className="self-start">
        Continue
      </Button>
    </form>
  );
}
