/**
 * Spec 218 Slice 218-5 — TextLongAsk shape renderer.
 *
 * Renders a multi-line textarea for long free-text input. Submits the
 * stripped value when non-empty. Disabled submit if the trimmed value
 * is empty.
 *
 * `max_chars` from the envelope drives the textarea `maxLength` so the
 * browser enforces the cap; the backend also validates ≤1000 chars for
 * the geek_out_on slot.
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";

import type { TextLongAsk } from "./types/envelope";

type Props = {
  envelope: TextLongAsk;
  onSubmit: (value: string) => void;
};

export function TextLongShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");

  const trimmed = value.trim();
  const canSubmit = trimmed.length > 0;

  return (
    <form
      data-testid="v2-text-long-shape"
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit(trimmed);
      }}
      className="flex flex-col gap-4"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={envelope.placeholder ?? ""}
        maxLength={envelope.max_chars ?? 500}
        rows={5}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
      />
      <Button type="submit" disabled={!canSubmit} className="self-start">
        Next
      </Button>
    </form>
  );
}
