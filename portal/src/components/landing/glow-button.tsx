"use client"

import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { ArrowUpRight } from "lucide-react"
import Link from "next/link"

interface GlowButtonProps {
  href: string
  children: React.ReactNode
  className?: string
  size?: "sm" | "md" | "lg"
}

const sizeClasses = {
  sm: "px-4 py-2 text-sm gap-1.5",
  md: "px-6 py-3 text-base gap-2",
  lg: "px-8 py-4 text-lg gap-2.5",
}

const isExternal = (href: string) =>
  href.startsWith("http://") || href.startsWith("https://") || href.startsWith("t.me")

export function GlowButton({ href, children, className, size = "md" }: GlowButtonProps) {
  return (
    <motion.div
      className="inline-flex"
      whileHover={{ scale: 1.03 }}
      whileFocus={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
    >
      <Link
        href={href}
        target={isExternal(href) ? "_blank" : undefined}
        rel={isExternal(href) ? "noopener noreferrer" : undefined}
        className={cn(
          "inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold glow-rose-pulse transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          sizeClasses[size],
          className
        )}
      >
        {children}
        <ArrowUpRight className="shrink-0" aria-hidden="true" />
      </Link>
    </motion.div>
  )
}
