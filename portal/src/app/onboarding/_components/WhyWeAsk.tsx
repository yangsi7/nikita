"use client"

/**
 * WhyWeAsk — third-person narrator-voice helper text under each headline.
 *
 * AC C1.9 + C1.20: a single sentence in narrator voice describing why
 * the slot is collected and how it tailors backstory + persona.
 *
 * `id` is required so the slot's `<textarea>` / `<input>` can reference
 * it via `aria-describedby` (C1.12 textarea pattern).
 */
export function WhyWeAsk({ id, text }: { id: string; text: string }) {
  return (
    <p id={id} className="text-sm text-foreground/60 mt-2">
      {text}
    </p>
  )
}
