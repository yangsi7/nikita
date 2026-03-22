"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { SectionHeader } from "../components/section-header"
import { NikitaQuote } from "../components/nikita-quote"
import { ChapterStepper } from "../components/chapter-stepper"

const CHAPTERS = [
  { number: 1, name: "Curiosity", tagline: "Where it all begins", locked: false },
  { number: 2, name: "Intrigue", tagline: "Things get real", locked: false },
  { number: 3, name: "???", tagline: "???", locked: true },
  { number: 4, name: "???", tagline: "???", locked: true },
  { number: 5, name: "???", tagline: "???", locked: true },
]

export function ChapterSection() {
  return (
    <section
      aria-label="The Chapters"
      data-testid="section-chapters"
      className="snap-start flex h-screen items-center justify-center px-4"
    >
      <div className="flex w-full max-w-[720px] flex-col items-center gap-8">
        <SectionHeader>The Chapters</SectionHeader>

        <NikitaQuote>
          &ldquo;We&apos;re just getting started... things get interesting
          later.&rdquo;
        </NikitaQuote>

        <ChapterStepper currentChapter={1} chapters={CHAPTERS} />

        <GlassCard className="w-full p-6">
          <h3 className="text-sm font-semibold text-foreground mb-2">
            Chapter I &mdash; Curiosity
          </h3>
          <NikitaQuote>
            &ldquo;This is where it all begins. I&apos;m watching you. Impress
            me and we move forward. Bore me and... well, let&apos;s not think
            about that yet.&rdquo;
          </NikitaQuote>
        </GlassCard>
      </div>
    </section>
  )
}
