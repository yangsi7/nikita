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
  slot: string;
  prompt: string;
  placeholder?: string;
  max_chars?: number;
  dictation?: boolean;
  autocomplete?: boolean;
};

export type TextLongAsk = {
  component: "text_long";
  slot: string;
  prompt: string;
  placeholder?: string;
  max_chars?: number;
  dictation?: boolean;
};

export type SingleSelectAsk = {
  component: "single_select";
  slot: string;
  prompt: string;
  options: Option[];
};

export type ChipMultiAsk = {
  component: "chip_multi";
  slot: string;
  prompt: string;
  options: Option[];
  min_pick?: number;
  max_pick?: number;
};

export type SliderAsk = {
  component: "slider";
  slot: string;
  prompt: string;
  min_val: number;
  max_val: number;
  step?: number;
  labels?: Record<number, string>;
};

export type CalendarAsk = {
  component: "calendar";
  slot: string;
  prompt: string;
  min_date?: string | null;
  max_date?: string | null;
};

export type PhoneAsk = {
  component: "phone";
  slot: "phone";
  prompt: string;
  default_country?: string;
  demo_call_after_submit?: boolean;
};

export type CompleteAsk = {
  component: "complete";
  next_route: string;
  backstory_preview?: string | null;
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
  | CompleteAsk;

/**
 * Component-name string literal type. Useful for narrowing in the
 * dispatcher and for compile-time exhaustiveness checks.
 */
export type AskComponent = AskUnion["component"];
