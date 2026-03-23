"use client"

import { motion, useInView, useReducedMotion } from "framer-motion"
import { useRef } from "react"

export function OnboardingMoodOrb() {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const reducedMotion = useReducedMotion()

  return (
    <div ref={ref} className="flex justify-center" data-testid="onboarding-mood-orb">
      <motion.div
        className="relative size-32 md:size-40 rounded-full"
        initial={{ scale: 0, opacity: 0 }}
        animate={isInView ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
        transition={{ type: "spring", stiffness: 80, damping: 12, mass: 1 }}
      >
        {/* Glow layer */}
        <motion.div
          className="absolute inset-0 rounded-full blur-xl"
          style={{
            background: "radial-gradient(circle, oklch(0.75 0.15 350 / 40%) 0%, oklch(0.75 0.15 350 / 0%) 70%)",
          }}
          animate={reducedMotion ? {} : { scale: [1, 1.15, 1], opacity: [0.6, 0.9, 0.6] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* Core orb */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: "radial-gradient(circle at 40% 35%, oklch(0.85 0.15 350) 0%, oklch(0.65 0.18 340) 40%, oklch(0.45 0.15 350) 100%)",
            boxShadow: "0 0 20px oklch(0.75 0.15 350 / 30%), inset 0 0 20px oklch(0.85 0.1 350 / 20%)",
          }}
          animate={reducedMotion ? {} : { scale: [1, 1.03, 1] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* Highlight */}
        <div
          className="absolute left-[30%] top-[20%] size-[20%] rounded-full"
          style={{
            background: "radial-gradient(circle, oklch(0.95 0.05 350 / 60%) 0%, transparent 100%)",
          }}
        />
      </motion.div>
    </div>
  )
}
