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
 *
 * Cluster X: replaced handroll <textarea> with shadcn Textarea
 * (per components.json shadcn-primitive rule).
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

import type { TextLongAsk } from "./types/envelope";

type Props = {
  envelope: TextLongAsk;
  onSubmit: (value: string) => void;
};

export function TextLongShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");

  // Backend hard limit is 1000 chars (nikita/api/routes/portal_onboarding_v2.py
  // _slot_payload geek_out_on branch). FE fallback mirrors the backend so a
  // payload missing max_chars cannot drift caps.
  const maxChars = envelope.max_chars ?? 1000;
  const trimmed = value.trim();
  // Length guard alongside non-empty: maxLength HTML attribute can be
  // bypassed by programmatic .value assignment or older mobile IMEs.
  const canSubmit = trimmed.length > 0 && trimmed.length <= maxChars;

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
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={envelope.placeholder ?? ""}
        maxLength={maxChars}
        rows={5}
        className="resize-none"
      />
      <Button type="submit" disabled={!canSubmit} className="self-start">
        Continue
      </Button>
    </form>
  );
}
