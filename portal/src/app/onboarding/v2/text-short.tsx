/**
 * Spec 218 Slice 218-2 — text_short shape renderer.
 *
 * Renders a single-line input bound to the envelope's `slot` + `prompt`.
 * Calls `onSubmit(value)` on form submit. `max_chars` enforced client-side
 * via `maxLength`; server-side validation lives in `TextShortAsk` Pydantic.
 *
 * Subsequent slices reuse this shape verbatim for any text_short slot.
 */

"use client";

import * as React from "react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import type { TextShortAsk } from "./types/envelope";

type Props = {
  envelope: TextShortAsk;
  onSubmit: (value: string) => void;
};

export function TextShortShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!value.trim()) return;
        onSubmit(value.trim());
      }}
      className="flex flex-col gap-3"
    >
      <label htmlFor={`v2-${envelope.slot}`} className="text-base text-foreground">
        {envelope.prompt}
      </label>
      <div className="flex gap-2">
        <Input
          id={`v2-${envelope.slot}`}
          aria-label={envelope.prompt}
          name={envelope.slot}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={envelope.placeholder ?? ""}
          maxLength={envelope.max_chars ?? 80}
          autoComplete={envelope.autocomplete ? "on" : "off"}
        />
        <Button type="submit" disabled={!value.trim()}>
          Continue
        </Button>
      </div>
    </form>
  );
}
