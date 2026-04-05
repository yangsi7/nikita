"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { GlowButton } from "./glow-button"

interface LandingNavProps {
  isAuthenticated: boolean
}

export function LandingNav({ isAuthenticated }: LandingNavProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const threshold = window.innerHeight * 0.5
    const handleScroll = () => {
      setVisible(window.scrollY > threshold)
    }
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const ctaHref = isAuthenticated ? "/dashboard" : "https://t.me/Nikita_my_bot"
  const ctaLabel = isAuthenticated ? "Go to Dashboard" : "Start Relationship"

  return (
    <motion.nav
      className={cn(
        "fixed top-0 inset-x-0 z-50 glass-card backdrop-blur border-b border-white/10",
        "flex items-center justify-between px-6 py-3"
      )}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: visible ? 1 : 0, y: visible ? 0 : -8 }}
      transition={{ duration: 0.3 }}
      // visibility:hidden prevents keyboard focus on invisible nav (a11y)
      style={{ visibility: visible ? "visible" : "hidden" }}
    >
      {/* Brand */}
      <Link href="/" className="text-foreground font-semibold text-sm tracking-tight">
        Nikita
      </Link>

      {/* CTA */}
      <GlowButton href={ctaHref} size="sm">
        {ctaLabel}
      </GlowButton>
    </motion.nav>
  )
}
