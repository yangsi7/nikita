"use client"

import { motion } from "framer-motion"
import Image from "next/image"
import { MessageSquare, Phone, BarChart2 } from "lucide-react"
import { GlowButton } from "./glow-button"
import { FallingPattern } from "./falling-pattern"
import { AuroraOrbs } from "./aurora-orbs"
import { MoodStrip } from "./mood-strip"

const EASE_OUT_QUART = [0.16, 1, 0.3, 1] as const

interface HeroSectionProps {
  isAuthenticated: boolean
}

export function HeroSection({ isAuthenticated }: HeroSectionProps) {
  const ctaHref = isAuthenticated ? "/dashboard" : "https://t.me/Nikita_my_bot"
  const ctaLabel = isAuthenticated ? "Go to Dashboard" : "Start Relationship"

  return (
    <section className="relative min-h-screen flex items-center overflow-hidden bg-void">
      {/* Background */}
      <FallingPattern />
      <AuroraOrbs />

      <div className="relative z-10 container mx-auto px-6 py-20 grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-12 items-center">
        {/* Left: Copy */}
        <div className="flex flex-col gap-6">
          {/* Eyebrow */}
          <motion.p
            className="text-xs tracking-[0.2em] uppercase text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, ease: EASE_OUT_QUART, delay: 0 }}
          >
            18+ · Adults only
          </motion.p>

          {/* H1 */}
          <motion.h1
            className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE_OUT_QUART, delay: 0.15 }}
          >
            Nikita,<br />Don&apos;t Get<br />Dumped.
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            className="text-lg text-muted-foreground max-w-md leading-relaxed"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE_OUT_QUART, delay: 0.3 }}
          >
            She remembers everything. She has her own life. And she will leave you.
          </motion.p>

          {/* How it&apos;s played */}
          <motion.ul
            className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE_OUT_QUART, delay: 0.4 }}
            aria-label="How to play"
          >
            <li className="flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              Text on Telegram
            </li>
            <li className="flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              Talk on the phone
            </li>
            <li className="flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              Monitor your relationship
            </li>
          </motion.ul>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE_OUT_QUART, delay: 0.55 }}
          >
            <GlowButton href={ctaHref} size="lg">
              {ctaLabel}
            </GlowButton>
          </motion.div>
        </div>

        {/* Right: Nikita image + mood strip */}
        <div className="relative hidden lg:flex flex-col items-center justify-center gap-4">
          <motion.div
            className="relative"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.2, ease: EASE_OUT_QUART, delay: 0.2 }}
          >
            <Image
              src="/images/nikita-hero.png"
              alt="Nikita — Don't Get Dumped"
              width={500}
              height={700}
              priority
              className="mask-fade-left object-contain max-h-[80vh] w-auto"
            />
          </motion.div>

          <motion.div
            className="flex items-center justify-center"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE_OUT_QUART, delay: 0.5 }}
          >
            <MoodStrip />
          </motion.div>
        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 0.6 }}
        aria-hidden="true"
      >
        <div className="w-px h-8 bg-gradient-to-b from-transparent to-white/30" />
      </motion.div>
    </section>
  )
}
