"use client"

import { useRef } from "react"
import { motion, useInView, useReducedMotion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { SectionHeader } from "../components/section-header"
import { NikitaQuote } from "../components/nikita-quote"
import { OnboardingMoodOrb } from "../components/onboarding-mood-orb"

interface MissionSectionProps {
  submitting: boolean
  error: string | null
  submitted?: boolean
}

export function MissionSection({ submitting, error, submitted = false }: MissionSectionProps) {
  const ref = useRef<HTMLElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.3 })
  const prefersReducedMotion = useReducedMotion()
  const show = prefersReducedMotion || isInView

  return (
    <section
      ref={ref}
      aria-label="Your Mission"
      className="snap-start flex h-screen items-center justify-center px-4"
      data-testid="section-mission"
    >
      <div className="flex w-full max-w-[720px] flex-col items-center gap-8 text-center">
        <OnboardingMoodOrb />
        <div className="h-6" /> {/* spacer */}

        <SectionHeader>Your Mission</SectionHeader>

        <h3 className="text-2xl font-bold tracking-tight text-foreground md:text-4xl">
          Don&apos;t Get Dumped
        </h3>

        <NikitaQuote className="max-w-md">
          &ldquo;Keep me interested. Keep me guessing. Make me feel something
          real. Or I walk.&rdquo;
        </NikitaQuote>

        {/* CTA Button */}
        <motion.div
          initial={
            prefersReducedMotion ? false : { opacity: 0, scale: 0.9 }
          }
          animate={
            show
              ? { opacity: 1, scale: 1 }
              : { opacity: 0, scale: 0.9 }
          }
          transition={{
            type: "spring",
            stiffness: 80,
            damping: 10,
            mass: 1,
          }}
        >
          <Button
            type="submit"
            size="lg"
            disabled={submitting}
            className={`h-12 px-8 text-base font-semibold hover:scale-[1.02] hover:shadow-[0_0_30px_oklch(0.75_0.15_350/50%)] transition-all duration-200${submitting ? "" : " glow-rose-pulse"}`}
            aria-label="Submit profile and start talking to Nikita"
            data-testid="onboarding-submit-btn"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <span className="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Saving...
              </span>
            ) : (
              "Start Talking to Nikita \u2192"
            )}
          </Button>
        </motion.div>

        {/* Error display */}
        {error && (
          <p
            role="alert"
            className="text-sm text-destructive max-w-md"
          >
            {error}
          </p>
        )}
      </div>

      {/* Telegram transition overlay */}
      {submitted && (
        <motion.div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 bg-void/95 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <OnboardingMoodOrb />
          <p className="text-lg font-medium text-foreground">Opening Telegram...</p>
          <motion.p
            className="text-sm text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 3, duration: 0.5 }}
          >
            <a href="https://t.me/Nikita_my_bot" className="underline hover:text-foreground transition-colors">
              Tap here if nothing happens
            </a>
          </motion.p>
        </motion.div>
      )}
    </section>
  )
}
