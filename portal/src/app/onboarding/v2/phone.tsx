/**
 * Spec 218 Slice 218-4 — PhoneAsk shape renderer.
 *
 * Renders a phone number input with an E.164 validation guard.
 * The input stores the raw typed value; on submit it passes through
 * as-is so the BE can apply its own E.164 regex gate.
 *
 * Note: react-phone-number-input is already in portal/package.json
 * (added by the voice-step legacy wizard); we do NOT add a second
 * phone input library here. For slice-218-4 the input is a plain
 * controlled <input> with a placeholder pattern. PR-218-6 will swap
 * this for the full libphonenumber-driven library component once the
 * voice demo-call flow is wired end-to-end.
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import type { PhoneAsk } from "./types/envelope";

type Props = {
  envelope: PhoneAsk;
  onSubmit: (value: string) => void;
};

// E.164 regex: starts with +, first digit non-zero, 6-14 more digits.
const E164_RE = /^\+[1-9]\d{6,14}$/;

export function PhoneShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");

  const isValid = E164_RE.test(value.trim());

  return (
    <form
      data-testid="v2-phone-shape"
      onSubmit={(e) => {
        e.preventDefault();
        const trimmed = value.trim();
        if (!E164_RE.test(trimmed)) return;
        onSubmit(trimmed);
      }}
      className="flex flex-col gap-4"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>
      <div className="flex flex-col gap-1">
        <Label htmlFor="v2-phone-input" className="text-sm text-muted-foreground">
          Phone number (E.164 format, e.g. +14155550100)
        </Label>
        <Input
          id="v2-phone-input"
          data-testid="v2-phone-input"
          type="tel"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={`+1 (${envelope.default_country}) ...`}
          autoComplete="tel"
          className="max-w-xs"
        />
      </div>
      <Button type="submit" disabled={!isValid} className="self-start">
        Next
      </Button>
    </form>
  );
}
