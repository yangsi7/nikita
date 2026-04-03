"use client"

// Custom text-shimmer — framer-motion equivalent of magicui.design/r/text-shimmer
// magicui.design/r/text-shimmer was unavailable in registry; implemented equivalent.

import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface TextShimmerProps {
  children: string
  className?: string
  duration?: number
}

export function TextShimmer({
  children,
  className,
  duration = 2,
}: TextShimmerProps) {
  return (
    <motion.span
      className={cn("relative inline-block", className)}
      style={{
        background: `linear-gradient(
          90deg,
          oklch(0.6 0 0) 0%,
          oklch(0.95 0 0) 40%,
          oklch(0.75 0.15 350) 50%,
          oklch(0.95 0 0) 60%,
          oklch(0.6 0 0) 100%
        )`,
        backgroundSize: "200% 100%",
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        WebkitTextFillColor: "transparent",
        color: "transparent",
      }}
      animate={{ backgroundPosition: ["200% 0", "-200% 0"] }}
      transition={{ duration, repeat: Infinity, ease: "linear" }}
    >
      {children}
    </motion.span>
  )
}
