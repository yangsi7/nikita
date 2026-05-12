"use client"

/**
 * PhoneDemoModal — FR-009 consent modal (Spec 218 slice 218-7)
 *
 * Renders a shadcn AlertDialog with:
 * - "Want Nikita to call you for ~10s?"
 * - Default-focused option: "Skip" (FR-009: default-skip protects accidental trigger)
 * - "Yes, call me" triggers POST /onboarding/phone-demo/consent
 */

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

export interface PhoneDemoModalProps {
  open: boolean
  onSkip: () => void
  onConsent: () => Promise<void>
  isLoading?: boolean
}

export function PhoneDemoModal({
  open,
  onSkip,
  onConsent,
  isLoading = false,
}: PhoneDemoModalProps) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Want Nikita to call you?</AlertDialogTitle>
          <AlertDialogDescription>
            She&apos;ll ring for about 10 seconds. One-time experience — never again.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          {/*
            Default-focused option is Skip (FR-009: default-skip protects against
            accidental call triggering). autoFocus on the cancel button ensures
            keyboard users default to the safe action.
          */}
          <AlertDialogCancel
            autoFocus
            onClick={onSkip}
            disabled={isLoading}
          >
            Skip
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={isLoading}
            onClick={() => {
              void onConsent()
            }}
          >
            {isLoading ? "Calling…" : "Yes, call me"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
