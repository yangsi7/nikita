/**
 * Spec 218 Slice 218-5 — SliderAsk shape renderer.
 *
 * Renders a horizontal slider with labelled tick marks. Uses the
 * shadcn/ui Slider (Radix primitive wrapper) from
 * `@/components/ui/slider`. Submits the selected int value via
 * `onSubmit(value)`.
 *
 * `labels` is a sparse map from int value to label string; rendered
 * below the track for the specified positions.
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

import type { SliderAsk } from "./types/envelope";

type Props = {
  envelope: SliderAsk;
  onSubmit: (value: number) => void;
};

export function SliderShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState(envelope.min_val);

  const handleValueChange = (values: number[]) => {
    setValue(values[0]);
  };

  return (
    <form
      data-testid="v2-slider-shape"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(value);
      }}
      className="flex flex-col gap-6"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>

      <div className="px-1">
        <Slider
          min={envelope.min_val}
          max={envelope.max_val}
          step={envelope.step ?? 1}
          defaultValue={[envelope.min_val]}
          onValueChange={handleValueChange}
          className="w-full"
          aria-label={envelope.prompt}
        />

        {/* Tick labels (sparse map) */}
        {envelope.labels && Object.keys(envelope.labels).length > 0 && (
          <div className="relative mt-2 h-5 text-xs text-muted-foreground select-none">
            {Object.entries(envelope.labels).map(([pos, label]) => {
              const numPos = Number(pos);
              const range = envelope.max_val - envelope.min_val;
              const pct =
                range === 0
                  ? 0
                  : ((numPos - envelope.min_val) / range) * 100;
              return (
                <span
                  key={pos}
                  className="absolute -translate-x-1/2"
                  style={{ left: `${pct}%` }}
                >
                  {label}
                </span>
              );
            })}
          </div>
        )}
      </div>

      <Button type="submit" className="self-start">
        Next
      </Button>
    </form>
  );
}
