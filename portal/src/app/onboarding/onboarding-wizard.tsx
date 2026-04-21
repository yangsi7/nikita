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
import {
  CONVERSATION_AGENT_TIMEOUT_MS,
  useConversationState,
} from "@/app/onboarding/hooks/useConversationState"
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
      // NR1b.1: build the user turn and pass the FULL conversation slice
      // (prior turns + this user turn) to the server. The reducer appends
      // the same turn locally; the server contract requires us to send the
      // turn we are about to emit, so it can extract fields + idempotency-
      // key the response. Using `state.turns` alone would omit the latest
      // user turn because React state updates are batched (N2 fix).
      // GH #376: do NOT put turn_id on the Turn itself. Backend Turn has
      // ConfigDict(extra='forbid'); turn_id lives only on the request envelope
      // (used for the Idempotency-Key header).
      const userTurn = {
        role: "user" as const,
        content: typeof input === "string" ? input : String(input.value),
        timestamp: new Date().toISOString(),
      }
      dispatch({ type: "user_input", input, turnId })
      try {
        const response = await api.converse(
          {
            conversation_history: [...state.turns, userTurn],
            user_input: input,
            turn_id: turnId,
          },
          AbortSignal.timeout(CONVERSATION_AGENT_TIMEOUT_MS)
        )
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
        // AbortSignal.timeout → AbortError (name === "AbortError") or
        // DOMException("TimeoutError"). Both route to the in-character
        // fallback bubble via the `timeout` reducer action (N1 fix).
        const maybeName = (err as { name?: string })?.name
        if (maybeName === "TimeoutError" || maybeName === "AbortError") {
          dispatch({ type: "timeout" })
          return
        }
        const maybeStatus = (err as { status?: number })?.status
        if (maybeStatus === 429) {
          const detail =
            (err as { detail?: { nikita_reply?: string } })?.detail
              ?.nikita_reply ?? "easy, tiger. give me a sec."
          // Fix I3 — preserve the prior control type/options on 429. The
          // previous hardcoded `next_prompt_type: "text"` silently demoted
          // any active chips/slider/toggle control to free-text on rate
          // limit, losing the user's inline affordance.
          dispatch({
            type: "server_response",
            response: {
              nikita_reply: detail,
              extracted_fields: {},
              confirmation_required: false,
              next_prompt_type: state.currentPromptType,
              next_prompt_options: state.currentPromptOptions ?? null,
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
    [
      api,
      dispatch,
      state.turns,
      state.progressPct,
      state.currentPromptType,
      state.currentPromptOptions,
    ]
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
    // Fix I4 — while the link-telegram mint is in flight (linkCode still
    // null and no mint error yet), render a neutral interstitial so we
    // don't flash the ceremony with a missing CTA. The ceremony itself
    // only paints once the code is available (or we explicitly failed and
    // need to surface `linkMintError`).
    if (!state.linkCode && !linkMintError) {
      return (
        <div
          data-testid="ceremony-loading"
          role="status"
          aria-live="polite"
          className="flex h-[100dvh] flex-col items-center justify-center gap-3 bg-background text-center text-sm text-muted-foreground"
        >
          <div
            aria-hidden="true"
            className="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-foreground"
          />
          <p>your file is closing...</p>
        </div>
      )
    }
    // Spec 214 T4.1 / AC-T4.1.3 (FR-11e): the ceremony hard-throws on a
    // null linkCode to prevent a silent-strand CTA pointing at
    // `t.me/Nikita_my_bot?start=` (Telegram would happily accept the
    // empty payload and the user would arrive without a binding token).
    // When the link-telegram mint failed AND we never received a code,
    // surface the error UI here instead of mounting the ceremony.
    if (!state.linkCode && linkMintError) {
      return (
        <div
          data-testid="ceremony-link-error"
          role="alert"
          className="flex h-[100dvh] flex-col items-center justify-center gap-4 bg-background px-6 text-center"
        >
          <p className="text-sm text-foreground/90">
            we couldn{"\u2019"}t generate your Telegram link.
          </p>
          <p className="text-xs text-muted-foreground">{linkMintError}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex h-10 items-center rounded-lg border border-foreground/20 px-5 text-sm"
          >
            try again
          </button>
        </div>
      )
    }
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
