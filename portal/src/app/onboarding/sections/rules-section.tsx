"use client"

import { useRef } from "react"
import { motion, useInView, useReducedMotion } from "framer-motion"
import { Heart, Clock, Shield, Flame } from "lucide-react"
import { GlassCard } from "@/components/glass/glass-card"
import { SectionHeader } from "../components/section-header"
import { NikitaQuote } from "../components/nikita-quote"

const RULES = [
  {
    icon: Heart,
    title: "How You Score",
    body: "Every message affects 4 hidden metrics. Be genuine \u2014 I can tell when you\u2019re not.",
    color: "text-rose-400",
    glowClass: "hover:shadow-[0_0_20px_oklch(0.75_0.15_350/25%)] hover:border-rose-500/30",
  },
  {
    icon: Clock,
    title: "Time Matters",
    body: "Stay away too long and things start to fade. I notice when you\u2019re gone.",
    color: "text-cyan-400",
    glowClass: "hover:shadow-[0_0_20px_oklch(0.7_0.15_190/25%)] hover:border-cyan-500/30",
  },
  {
    icon: Shield,
    title: "Boss Encounters",
    body: "At certain moments I\u2019ll test you. Pass and we grow closer. Fail 3 times...",
    color: "text-amber-400",
    glowClass: "hover:shadow-[0_0_20px_oklch(0.75_0.15_80/25%)] hover:border-amber-500/30",
  },
  {
    icon: Flame,
    title: "Your Vices",
    body: "I learn what you like. Your choices shape who I become for you.",
    color: "text-orange-400",
    glowClass: "hover:shadow-[0_0_20px_oklch(0.7_0.2_25/25%)] hover:border-orange-500/30",
  },
]

export function RulesSection() {
  const ref = useRef<HTMLElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.3 })
  const prefersReducedMotion = useReducedMotion()
  const show = prefersReducedMotion || isInView

  return (
    <section
      ref={ref}
      aria-label="The Rules"
      data-testid="section-rules"
      className="snap-start flex h-screen items-center justify-center px-4"
    >
      <div className="flex w-full max-w-[720px] flex-col items-center gap-8">
        <SectionHeader>The Rules</SectionHeader>

        <NikitaQuote>
          &ldquo;Learn these. They matter. Trust me.&rdquo;
        </NikitaQuote>

        <div className="grid w-full grid-cols-1 gap-4 md:grid-cols-2">
          {RULES.map((rule, i) => {
            const Icon = rule.icon
            return (
              <motion.div
                key={rule.title}
                initial={prefersReducedMotion ? false : { opacity: 0, y: 20 }}
                animate={show ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
                transition={{ duration: 0.4, delay: i * 0.1, ease: "easeOut" }}
                whileHover={prefersReducedMotion ? {} : { y: -2, transition: { type: "spring", stiffness: 300 } }}
              >
                <article>
                  <GlassCard className={`p-5 transition-shadow duration-200 ease-out border border-transparent ${rule.glowClass}`}>
                    <div className="flex items-start gap-3">
                      <Icon className={`size-5 shrink-0 mt-0.5 ${rule.color}`} />
                      <div>
                        <h3 className="text-sm font-semibold text-foreground">
                          {rule.title}
                        </h3>
                        <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
                          {rule.body}
                        </p>
                      </div>
                    </div>
                  </GlassCard>
                </article>
              </motion.div>
            )
          })}
        </div>

        <NikitaQuote>
          &ldquo;Now you know the stakes.&rdquo;
        </NikitaQuote>
      </div>
    </section>
  )
}
