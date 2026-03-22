"use client"

import { useRef } from "react"
import { useFormContext } from "react-hook-form"
import { motion, useInView, useReducedMotion } from "framer-motion"
import { GlassCard } from "@/components/glass/glass-card"
import { Input } from "@/components/ui/input"
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form"
import { SectionHeader } from "../components/section-header"
import { NikitaQuote } from "../components/nikita-quote"
import { SceneSelector } from "../components/scene-selector"
import { EdginessSlider } from "../components/edginess-slider"
import type { ProfileFormValues } from "../schemas"

export function ProfileSection() {
  const ref = useRef<HTMLElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.2 })
  const prefersReducedMotion = useReducedMotion()
  const show = prefersReducedMotion || isInView

  const form = useFormContext<ProfileFormValues>()

  return (
    <section
      ref={ref}
      aria-label="Who Are You"
      data-testid="section-profile"
      className="relative snap-start flex min-h-screen items-center justify-center px-4 py-16"
    >
      {/* Ambient rose glow behind form */}
      <div className="pointer-events-none absolute -z-10 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <motion.div
          className="size-96 rounded-full bg-rose-500/[0.03] blur-3xl"
          animate={prefersReducedMotion ? {} : { scale: [1, 1.02, 1] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      <motion.div
        className="flex w-full max-w-[720px] flex-col items-center gap-8"
        initial={prefersReducedMotion ? false : { opacity: 0, y: 20 }}
        animate={show ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <SectionHeader>Who Are You?</SectionHeader>

        <NikitaQuote>
          &ldquo;Before we really get started... tell me about you.&rdquo;
        </NikitaQuote>

        {/* Location input */}
        <GlassCard className="w-full p-5">
          <FormField
            control={form.control}
            name="location_city"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm text-muted-foreground">
                  Where are you?
                </FormLabel>
                <FormControl>
                  <Input
                    placeholder="City, Country"
                    aria-required="true"
                    {...field}
                  />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
        </GlassCard>

        {/* Scene selector */}
        <GlassCard className="w-full p-5">
          <FormField
            control={form.control}
            name="social_scene"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm text-muted-foreground">
                  What&apos;s your scene?
                </FormLabel>
                <FormControl>
                  <SceneSelector
                    value={field.value ?? null}
                    onChange={field.onChange}
                  />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
        </GlassCard>

        {/* Edginess slider */}
        <GlassCard className="w-full p-5">
          <FormField
            control={form.control}
            name="drug_tolerance"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm text-muted-foreground">
                  How edgy should I be?
                </FormLabel>
                <FormControl>
                  <EdginessSlider
                    value={field.value}
                    onChange={field.onChange}
                  />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
        </GlassCard>
      </motion.div>
    </section>
  )
}
