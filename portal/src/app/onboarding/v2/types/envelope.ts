/**
 * Spec 218 wizard v2 envelope type — TS mirror of
 * `nikita/agents/onboarding/v2/envelope.py`.
 *
 * 8 component shapes per FR-005 (NO MORE — adding a 9th re-introduces
 * the sibling-stream pattern that motivated bulldozing 217). Reaction
 * text is folded into the next Ask's `prompt` field; there is NO
 * `reaction_only` shape.
 *
 * Discriminator: `component` (string literal per shape). Use `switch`
 * narrowing in `DynamicQuestion.tsx` (the dispatcher component, wired
 * in PR-218-4).
 */

export type Option = {
  value: string;
  label: string;
  blurb?: string | null;
};

// ---------------------------------------------------------------------------
// Per-shape Ask types
// ---------------------------------------------------------------------------

export type TextShortAsk = {
  component: "text_short";
  handler: "v2";
  slot: string;
  prompt: string;
  placeholder?: string;
  max_chars?: number;
  dictation?: boolean;
  autocomplete?: boolean;
  /** Slots that the router invalidated this turn (FR-007). FE clears their state. */
  invalidated?: string[];
};

export type TextLongAsk = {
  component: "text_long";
  handler: "v2";
  slot: string;
  prompt: string;
  placeholder?: string;
  max_chars?: number;
  dictation?: boolean;
  invalidated?: string[];
};

export type SingleSelectAsk = {
  component: "single_select";
  handler: "v2";
  slot: string;
  prompt: string;
  options: Option[];
  invalidated?: string[];
};

export type ChipMultiAsk = {
  component: "chip_multi";
  handler: "v2";
  slot: string;
  prompt: string;
  options: Option[];
  min_pick?: number;
  max_pick?: number;
  invalidated?: string[];
};

export type SliderAsk = {
  component: "slider";
  handler: "v2";
  slot: string;
  prompt: string;
  min_val: number;
  max_val: number;
  step?: number;
  labels?: Record<number, string>;
  invalidated?: string[];
};

export type CalendarAsk = {
  component: "calendar";
  handler: "v2";
  slot: string;
  prompt: string;
  min_date?: string | null;
  max_date?: string | null;
  invalidated?: string[];
};

export type PhoneAsk = {
  component: "phone";
  handler: "v2";
  slot: "phone";
  prompt: string;
  default_country?: string;
  demo_call_after_submit?: boolean;
  invalidated?: string[];
};

export type CompleteAsk = {
  component: "complete";
  handler: "v2";
  next_route: string;
  backstory_preview?: string | null;
};

/**
 * Spec 218 Slice 218-2 R14 — hand the next slot to the v1 wizard.
 *
 * Emitted when the user's session lands on a slot NOT covered by the
 * deployed slice's v2 surface. FE dispatcher switches on `handler`
 * BEFORE `component` and mounts the legacy v1 wizard for the remainder.
 *
 * Removed atomically with v1 deletion in PR-218-8.
 */
export type HandlerHandoffAsk = {
  component: "handler_handoff";
  handler: "v1";
  next_url: string;
};

// ---------------------------------------------------------------------------
// AskUnion — discriminated union (mirror of Pydantic `AskUnion`)
// ---------------------------------------------------------------------------

export type AskUnion =
  | TextShortAsk
  | TextLongAsk
  | SingleSelectAsk
  | ChipMultiAsk
  | SliderAsk
  | CalendarAsk
  | PhoneAsk
  | CompleteAsk
  | HandlerHandoffAsk;

/**
 * Component-name string literal type. Useful for narrowing in the
 * dispatcher and for compile-time exhaustiveness checks.
 */
export type AskComponent = AskUnion["component"];
