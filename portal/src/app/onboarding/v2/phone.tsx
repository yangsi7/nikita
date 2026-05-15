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
 *
 * Slice 218-8 cleanup: wire phone-demo modal when demo_call_after_submit=true.
 * State machine:
 *   idle → submitted_with_demo → (modal skip) → call onSubmit
 *                              → (modal consent) → (takeover complete) → call onSubmit
 */

"use client";

import * as React from "react";

import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PhoneDemoModal } from "./phone_demo_modal";
import { PhoneDemoTakeover } from "./phone_demo_takeover";

import type { PhoneAsk } from "./types/envelope";

type Props = {
  envelope: PhoneAsk;
  onSubmit: (value: string) => void;
};

// E.164 regex: starts with +, first digit non-zero, 6-14 more digits.
const E164_RE = /^\+[1-9]\d{6,14}$/;

type DemoPhase = "idle" | "modal" | "takeover";

export function PhoneShape({ envelope, onSubmit }: Props) {
  const [value, setValue] = React.useState("");
  const [demoPhase, setDemoPhase] = React.useState<DemoPhase>("idle");
  const [pendingPhone, setPendingPhone] = React.useState<string | null>(null);
  const [userId, setUserId] = React.useState<string | null>(null);
  const [modalLoading, setModalLoading] = React.useState(false);

  const supabase = React.useMemo(() => createClient(), []);

  // Prefetch userId when demo_call_after_submit is true so it's ready when needed.
  React.useEffect(() => {
    if (!envelope.demo_call_after_submit) return;
    void supabase.auth.getSession().then(({ data: { session } }) => {
      setUserId(session?.user?.id ?? null);
    });
  }, [envelope.demo_call_after_submit, supabase]);

  const isValid = E164_RE.test(value.trim());

  async function handleConsent(): Promise<void> {
    if (!pendingPhone) return;
    setModalLoading(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      await fetch("/api/v1/onboarding/phone-demo/consent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ phone_e164: pendingPhone }),
      });
    } finally {
      setModalLoading(false);
    }
    setDemoPhase("takeover");
  }

  function handleSkip(): void {
    setDemoPhase("idle");
    if (pendingPhone) onSubmit(pendingPhone);
  }

  function handleTakeoverComplete(): void {
    setDemoPhase("idle");
    if (pendingPhone) onSubmit(pendingPhone);
  }

  // Show takeover full-screen during phone-demo call.
  if (demoPhase === "takeover" && userId) {
    return (
      <PhoneDemoTakeover
        userId={userId}
        onComplete={handleTakeoverComplete}
      />
    );
  }

  return (
    <>
      <form
        data-testid="v2-phone-shape"
        onSubmit={(e) => {
          e.preventDefault();
          const trimmed = value.trim();
          if (!E164_RE.test(trimmed)) return;
          if (envelope.demo_call_after_submit) {
            setPendingPhone(trimmed);
            setDemoPhase("modal");
          } else {
            onSubmit(trimmed);
          }
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
            placeholder="+1 415 555 0100"
            autoComplete="tel"
            className="max-w-xs"
          />
        </div>
        <Button type="submit" disabled={!isValid} className="self-start">
          Next
        </Button>
      </form>
      {demoPhase === "modal" && (
        <PhoneDemoModal
          open
          onSkip={handleSkip}
          onConsent={handleConsent}
          isLoading={modalLoading}
        />
      )}
    </>
  );
}
