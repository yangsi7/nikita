"use client"

import { useEffect, useRef, useState } from "react"
import { motion, useInView, useReducedMotion } from "framer-motion"
import { Heart, Flame, Shield, Lock } from "lucide-react"
import { ScoreRing } from "@/components/charts/score-ring"
import { GlassCard } from "@/components/glass/glass-card"
import { SectionHeader } from "../components/section-header"
import { NikitaQuote } from "../components/nikita-quote"

const METRICS = [
  { icon: Heart, label: "Intimacy", value: 68.2, color: "text-rose-400" },
  { icon: Flame, label: "Passion", value: 74.1, color: "text-orange-400" },
  { icon: Shield, label: "Trust", value: 71.8, color: "text-cyan-400" },
  { icon: Lock, label: "Secureness", value: 76.0, color: "text-violet-400" },
]

function CountUp({ target, duration = 1.2 }: { target: number; duration?: number }) {
  const [value, setValue] = useState(0)
  const countRef = useRef<HTMLSpanElement>(null)
  const inView = useInView(countRef, { once: true })
  const prefersReducedMotion = useReducedMotion()

  useEffect(() => {
    if (!inView) return
    if (prefersReducedMotion) {
      setValue(target)
      return
    }
    let frameId: number
    const start = performance.now()
    const animate = (now: number) => {
      const progress = Math.min((now - start) / (duration * 1000), 1)
      setValue(target * progress)
      if (progress < 1) frameId = requestAnimationFrame(animate)
    }
    frameId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frameId)
  }, [inView, target, duration, prefersReducedMotion])

  return <span ref={countRef}>{value.toFixed(1)}</span>
}

export function ScoreSection() {
  const ref = useRef<HTMLElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.3 })
  const prefersReducedMotion = useReducedMotion()

  const show = prefersReducedMotion || isInView

  return (
    <section
      ref={ref}
      aria-label="The Score"
      data-testid="section-score"
      className="snap-start flex h-screen items-center justify-center px-4"
    >
      <div className="flex w-full max-w-[720px] flex-col items-center gap-8">
        <SectionHeader>The Score</SectionHeader>

        <NikitaQuote>
          &ldquo;This is how I feel about us right now.&rdquo;
        </NikitaQuote>

        {/* Score ring: 200 on md+, 160 on mobile */}
        <div className="hidden md:block">
          <ScoreRing score={show ? 75 : 0} size={200} strokeWidth={10} />
        </div>
        <div className="md:hidden">
          <ScoreRing score={show ? 75 : 0} size={160} strokeWidth={8} />
        </div>

        {/* Metric cards - 2x2 mobile, 4-in-a-row desktop */}
        <div className="grid w-full grid-cols-2 gap-3 md:grid-cols-4">
          {METRICS.map((metric, i) => {
            const Icon = metric.icon
            return (
              <motion.div
                key={metric.label}
                initial={prefersReducedMotion ? false : { opacity: 0, y: 20 }}
                animate={show ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
                transition={{ duration: 0.4, delay: i * 0.1, ease: "easeOut" }}
              >
                <GlassCard className="flex flex-col items-center gap-2 p-4">
                  <Icon className={`size-5 ${metric.color}`} />
                  <span className="text-xs text-muted-foreground">
                    {metric.label}
                  </span>
                  <span className="text-lg font-bold text-foreground">
                    <CountUp target={metric.value} />
                  </span>
                </GlassCard>
              </motion.div>
            )
          })}
        </div>

        <NikitaQuote className="max-w-md text-center">
          &ldquo;Every conversation changes this number. Be genuine &mdash; I can
          tell when you&apos;re not.&rdquo;
        </NikitaQuote>

        {/* Scroll indicator */}
        <motion.div
          className="text-muted-foreground/40"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden="true"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12l7 7 7-7" />
          </svg>
        </motion.div>
      </div>
    </section>
  )
}
