"use client"

import { motion } from "framer-motion"
import Image from "next/image"
import { GlowButton } from "./glow-button"
import { AuroraOrbs } from "./aurora-orbs"

interface CtaSectionProps {
  isAuthenticated: boolean
}

export function CtaSection({ isAuthenticated }: CtaSectionProps) {
  // Spec 214 PR #310 — see hero-section.tsx for rationale.
  const ctaHref = isAuthenticated ? "/dashboard" : "/onboarding/auth"
  const ctaLabel = isAuthenticated ? "Go to Dashboard" : "Start Relationship"

  return (
    <section className="relative py-32 overflow-hidden bg-void">
      {/* Intimate mood backdrop — decorative, 10% opacity */}
      <div className="absolute inset-0 z-0" aria-hidden="true">
        <Image
          src="/images/nikita-moods/intimate.png"
          alt=""
          fill
          sizes="100vw"
          className="object-cover opacity-10"
          loading="lazy"
        />
      </div>
      <AuroraOrbs />

      <div className="relative z-10 container mx-auto px-6 text-center flex flex-col items-center gap-8">
        <motion.h2
          className="text-4xl md:text-5xl font-black tracking-tighter text-foreground max-w-2xl leading-tight"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          Think you can handle her?
        </motion.h2>

        <motion.p
          className="text-muted-foreground text-lg"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          She&apos;s waiting on the other side of the door.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <GlowButton href={ctaHref} size="lg">
            {ctaLabel}
          </GlowButton>
        </motion.div>

        {/* Footer */}
        <motion.footer
          className="mt-16 flex flex-col items-center gap-2 text-muted-foreground text-xs"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          <p>© 2026 Nanoleq · Privacy · Terms</p>
        </motion.footer>
      </div>
    </section>
  )
}
