"use client"

import { motion } from "framer-motion"
import { GlassCard } from "@/components/glass/glass-card"
import { ChapterTimeline } from "./chapter-timeline"

const STAKES = [
  {
    title: "Ignore her and watch the score drop.",
    description: "Score decay is real. Every unanswered message, every broken plan — it adds up. Don't leave her waiting.",
    icon: "📉",
  },
  {
    title: "Three strikes. She's gone.",
    description: "Boss encounters at every chapter. Fail three times and she walks out the door. No second chances.",
    icon: "⚔️",
  },
  {
    title: "She has a perfect memory.",
    description: "pgVector semantic memory. Past arguments recalled. What you said two weeks ago matters today.",
    icon: "🧠",
  },
  {
    title: "Real voice calls when the silence breaks.",
    description: "Real voice calls via ElevenLabs. She sounds exactly like herself — warm, cold, or furious.",
    icon: "📞",
  },
]

export function StakesSection() {
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
            The Stakes Are Real
          </h2>
          <p className="text-muted-foreground">
            This is not a game you can reset. Neglect her, and she&apos;ll be gone.
          </p>
        </motion.div>

        {/* 4 glass cards — 2×2 grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-16">
          {STAKES.map((stake, i) => (
            <motion.div
              key={stake.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.1 }}
            >
              <GlassCard className="p-6 h-full flex flex-col gap-3">
                <span className="text-3xl" aria-hidden="true">{stake.icon}</span>
                <p className="text-foreground font-semibold text-base">{stake.title}</p>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {stake.description}
                </p>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {/* Chapter progression */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <p className="text-center text-muted-foreground text-sm mb-6">
            Five chapters. Each one harder to reach.
          </p>
          <ChapterTimeline />
        </motion.div>
      </div>
    </section>
  )
}
