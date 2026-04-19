"use client"

/**
 * ConfirmationButtons — Spec 214 T3.7.
 *
 * Renders `[Yes] [Fix that]` inline below the most recent Nikita bubble when
 * `confirmation_required=true` (AC-T3.7.1). `Fix that` triggers the ghost-turn
 * flow: the parent dispatches `reject_confirmation` (which marks the latest
 * Nikita turn superseded and clears pending control), then re-sends an
 * empty-turn confirm-rejection POST so the server acknowledges the correction
 * in its next bubble.
 */

export interface ConfirmationButtonsProps {
  onConfirm: () => void
  onReject: () => void
  disabled?: boolean
}

export function ConfirmationButtons({
  onConfirm,
  onReject,
  disabled,
}: ConfirmationButtonsProps) {
  return (
    <div
      data-testid="confirmation-buttons"
      className="flex items-center gap-2 py-2"
    >
      <button
        type="button"
        data-testid="confirmation-yes"
        disabled={disabled}
        onClick={onConfirm}
        className="h-11 min-w-[44px] min-h-[44px] rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        yes
      </button>
      <button
        type="button"
        data-testid="confirmation-fix"
        disabled={disabled}
        onClick={onReject}
        className="h-11 min-w-[44px] min-h-[44px] rounded-xl border border-input bg-background px-4 text-sm disabled:opacity-50"
      >
        fix that
      </button>
    </div>
  )
}
