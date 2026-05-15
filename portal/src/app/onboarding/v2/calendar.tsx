/**
 * Spec 218 Slice 218-3 — CalendarAsk shape renderer.
 *
 * Renders a native `<input type="date">` (via shadcn Input) bound to
 * the envelope's slot + prompt. Returns ISO date string ("YYYY-MM-DD")
 * on submit; backend computes age int from the DoB.
 *
 * Trade-off: native date input is browser-rendered (vs shadcn Calendar
 * + Popover). Slice 218-6 may upgrade to the richer DayPicker UX if
 * dogfood walks surface DoB UX friction. For now this satisfies the
 * shadcn-via-components.json rule (shadcn Input passes through `type`)
 * and keeps the test surface trivial.
 *
 * min_date / max_date envelope fields constrain the browser picker
 * via the `min` / `max` attributes (HTML5 native).
 */

"use client";

import * as React from "react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import type { CalendarAsk } from "./types/envelope";

type Props = {
  envelope: CalendarAsk;
  onSubmit: (isoDate: string) => void;
};

export function CalendarShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");

  // Age gate: compute the ISO date 18 years ago today (Cluster D — Phase-2 fix plan).
  // The browser date picker enforces this via the `max` attribute so users
  // cannot select an underage DoB. The server also enforces age >= 18 via
  // HTTP 400 age_below_minimum if the FE constraint is bypassed.
  const eighteenYearsAgo = React.useMemo(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 18);
    return d.toISOString().split("T")[0]; // "YYYY-MM-DD"
  }, []);

  return (
    <form
      data-testid="v2-calendar-shape"
      onSubmit={(e) => {
        e.preventDefault();
        if (!value) return;
        onSubmit(value);
      }}
      className="flex flex-col gap-3"
    >
      <label
        htmlFor={`v2-${envelope.slot}`}
        className="text-base text-foreground"
      >
        {envelope.prompt}
      </label>
      <div className="flex gap-2">
        <Input
          id={`v2-${envelope.slot}`}
          type="date"
          aria-label={envelope.prompt}
          name={envelope.slot}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          min={envelope.min_date ?? undefined}
          max={envelope.max_date ?? eighteenYearsAgo}
        />
        <Button type="submit" disabled={!value}>
          Next
        </Button>
      </div>
    </form>
  );
}
