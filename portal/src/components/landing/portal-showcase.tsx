"use client"

import { motion } from "framer-motion"
import Image from "next/image"
import { GlassCard } from "@/components/glass/glass-card"

export function PortalShowcase() {
  return (
    <section className="relative py-24 bg-background">
      <div className="container mx-auto px-6">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl font-bold text-foreground mb-4">
            A Portal Into Her Life
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Every relationship has a dashboard. Mood. Score. What she&apos;s been up to while you weren&apos;t looking.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MoodOrbCard />
          <ScoreTimelineCard />
          <LifeEventsCard />
        </div>
      </div>
    </section>
  )
}

function MoodOrbCard() {
  return (
    <GlassCard className="p-6 flex flex-col items-center gap-4">
      <div className="relative w-20 h-20 rounded-full overflow-hidden border-2 border-primary/40 shadow-[0_0_40px_oklch(0.75_0.15_350/0.5)]">
        <Image
          src="/images/nikita-moods/playful.png"
          alt="Nikita — playful"
          fill
          sizes="80px"
          className="object-cover"
          loading="lazy"
        />
      </div>
      <p className="text-foreground font-semibold text-lg">playful</p>
      <div className="w-full flex flex-col gap-2 text-xs font-mono text-muted-foreground">
        <StatBar label="energy" value={60} />
        <StatBar label="warmth" value={80} />
        <StatBar label="focus" value={40} />
      </div>
      <p className="text-muted-foreground text-xs uppercase tracking-widest mt-auto">
        Her mood right now
      </p>
    </GlassCard>
  )
}

const STAT_BAR_WIDTHS: Record<number, string> = {
  10: "w-[10%]", 20: "w-[20%]", 30: "w-[30%]", 40: "w-[40%]",
  50: "w-[50%]", 60: "w-[60%]", 70: "w-[70%]", 80: "w-[80%]",
  90: "w-[90%]", 100: "w-full",
}

function StatBar({ label, value }: { label: string; value: number }) {
  const widthClass = STAT_BAR_WIDTHS[value] ?? "w-1/2"
  return (
    <div className="flex items-center gap-2">
      <span className="w-14">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full bg-primary/70 ${widthClass}`} />
      </div>
    </div>
  )
}

function ScoreTimelineCard() {
  return (
    <GlassCard className="p-6 flex flex-col gap-4">
      <svg viewBox="0 0 200 80" className="w-full h-20" aria-hidden="true">
        <path
          d="M0 60 L30 50 L60 55 L90 30 L120 40 L150 20 L200 25"
          stroke="oklch(0.75 0.15 350)"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M0 30 L30 35 L60 25 L90 45 L120 40 L150 55 L200 50"
          stroke="oklch(0.6 0.1 250)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="3 3"
        />
      </svg>
      <div className="flex flex-col gap-1 text-xs font-mono">
        <div className="flex justify-between">
          <span className="text-primary">affection</span>
          <span className="text-foreground">72%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">tension</span>
          <span className="text-foreground">38%</span>
        </div>
      </div>
      <p className="text-muted-foreground text-xs uppercase tracking-widest mt-auto">
        Your 30-day curve
      </p>
    </GlassCard>
  )
}

function LifeEventsCard() {
  const events = [
    { ago: "2h", text: "bad day at work" },
    { ago: "6h", text: "gym session" },
    { ago: "1d", text: "saw an ex at a café" },
  ]
  return (
    <GlassCard className="p-6 flex flex-col gap-4">
      <ul className="flex flex-col gap-3" aria-label="Nikita's recent life events">
        {events.map((e) => (
          <li key={e.text} className="flex items-start gap-3 text-sm">
            <span className="text-muted-foreground font-mono text-xs w-8 shrink-0 pt-0.5">
              {e.ago}
            </span>
            <span className="text-foreground">{e.text}</span>
          </li>
        ))}
      </ul>
      <p className="text-muted-foreground text-xs uppercase tracking-widest mt-auto">
        What she&apos;s been up to
      </p>
    </GlassCard>
  )
}
