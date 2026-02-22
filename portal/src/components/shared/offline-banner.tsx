"use client"

import { WifiOff } from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { useOnlineStatus } from "@/hooks/use-online-status"

export function OfflineBanner() {
  const isOnline = useOnlineStatus()

  return (
    <AnimatePresence>
      {!isOnline && (
        <motion.div
          initial={{ opacity: 0, y: -40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -40 }}
          transition={{ duration: 0.3 }}
          className="glass-card-amber fixed inset-x-0 top-0 z-50 flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-amber-400"
          role="alert"
        >
          <WifiOff className="h-4 w-4 shrink-0" />
          <span>You&apos;re offline. Some features may be unavailable.</span>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
