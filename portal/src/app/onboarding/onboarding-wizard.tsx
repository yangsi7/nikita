"use client"

/**
 * OnboardingWizard — Spec 214 FR-11d chat-first rewrite (T3.9).
 *
 * Single chat driver: `ChatShell` surfaces turns from `useConversationState`
 * while the reducer handles /converse responses. On
 * `response.conversation_complete=true` the wizard mints a fresh
 * link-telegram code via POST /portal/link-telegram BEFORE
 * `ClearanceGrantedCeremony` paints (AC-T3.9.4).
 *
 * Feature flag (AC-T3.9.2): `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD=true` routes
 * to the legacy step-by-step wizard kept under `steps/legacy/`. Default is
 * false (chat wizard ships production).
 */

import { useCallback, useEffect, useRef, useState } from "react"

import { ChatShell } from "@/app/onboarding/components/ChatShell"
import { ClearanceGrantedCeremony } from "@/app/onboarding/components/ClearanceGrantedCeremony"
import { ConfirmationButtons } from "@/app/onboarding/components/ConfirmationButtons"
import { InlineControl } from "@/app/onboarding/components/InlineControl"
import { ProgressHeader } from "@/app/onboarding/components/ProgressHeader"
import { useConversationState } from "@/app/onboarding/hooks/useConversationState"
import { useOnboardingAPI } from "@/app/onboarding/hooks/use-onboarding-api"
import type { ControlSelection } from "@/app/onboarding/types/ControlSelection"
import { LegacyOnboardingWizard } from "@/app/onboarding/onboarding-wizard-legacy"

export interface OnboardingWizardProps {
  userId: string
}

function isLegacyFlagOn(): boolean {
  if (typeof process === "undefined") return false
  return process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD === "true"
}

export function OnboardingWizard(props: OnboardingWizardProps) {
  if (isLegacyFlagOn()) {
    return <LegacyOnboardingWizard {...props} />
  }
  return <ChatOnboardingWizard {...props} />
}

function ChatOnboardingWizard({ userId }: OnboardingWizardProps) {
  const { state, dispatch, hydrateOnce } = useConversationState()
  const api = useOnboardingAPI()
  const hydratedRef = useRef(false)
  const [linkMintError, setLinkMintError] = useState<string | null>(null)

  useEffect(() => {
    if (hydratedRef.current) return
    hydratedRef.current = true
    hydrateOnce({
      turns: [
        {
          role: "nikita",
          content:
            "hey. building your file. where do i find you on a thursday night?",
          timestamp: new Date().toISOString(),
          source: "llm",
        },
      ],
      extractedFields: {},
      progressPct: 0,
      awaitingConfirmation: false,
      currentPromptType: "text",
    })
  }, [hydrateOnce, userId])

  const submit = useCallback(
    async (input: string | ControlSelection) => {
      const turnId = crypto.randomUUID()
      dispatch({ type: "user_input", input, turnId })
      try {
        const response = await api.converse({
          conversation_history: state.turns,
          user_input: input,
          turn_id: turnId,
        })
        dispatch({ type: "server_response", response })
        if (response.conversation_complete) {
          try {
            const link = await api.linkTelegram()
            dispatch({
              type: "link_code",
              code: link.code,
              expiresAt: link.expires_at,
            })
          } catch (err) {
            setLinkMintError("link mint failed")
            console.error("[onboarding] link_telegram mint failed", err)
          }
        }
      } catch (err) {
        const maybeStatus = (err as { status?: number })?.status
        if (maybeStatus === 429) {
          const detail =
            (err as { detail?: { nikita_reply?: string } })?.detail
              ?.nikita_reply ?? "easy, tiger. give me a sec."
          dispatch({
            type: "server_response",
            response: {
              nikita_reply: detail,
              extracted_fields: {},
              confirmation_required: false,
              next_prompt_type: "text",
              progress_pct: state.progressPct,
              conversation_complete: false,
              source: "fallback",
              latency_ms: 0,
            },
          })
          return
        }
        dispatch({ type: "server_error", error: "network error" })
      }
    },
    [api, dispatch, state.turns, state.progressPct]
  )

  const confirm = useCallback(() => {
    dispatch({ type: "confirm" })
    void submit("yes")
  }, [dispatch, submit])

  const reject = useCallback(() => {
    dispatch({ type: "reject_confirmation" })
    void submit("no, fix that")
  }, [dispatch, submit])

  if (state.isComplete) {
    return <ClearanceGrantedCeremony linkCode={state.linkCode ?? null} />
  }

  const footer = (
    <div className="flex flex-col gap-3">
      {linkMintError ? (
        <p className="text-xs text-destructive">{linkMintError}</p>
      ) : null}
      {state.awaitingConfirmation ? (
        <ConfirmationButtons
          disabled={state.isLoading}
          onConfirm={confirm}
          onReject={reject}
        />
      ) : (
        <InlineControl
          promptType={state.currentPromptType}
          options={state.currentPromptOptions}
          disabled={state.isLoading}
          onSubmit={submit}
        />
      )}
    </div>
  )

  return (
    <ChatShell
      turns={state.turns}
      isLoading={state.isLoading}
      header={<ProgressHeader progressPct={state.progressPct} />}
      footer={footer}
    />
  )
}
