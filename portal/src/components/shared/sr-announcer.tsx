"use client"

import { useEffect, useState } from "react"

let announceCallback: ((message: string) => void) | null = null

/**
 * Announce a message to screen readers via aria-live region.
 */
export function announce(message: string) {
  if (announceCallback) {
    announceCallback(message)
  }
}

export function SrAnnouncer() {
  const [message, setMessage] = useState("")

  useEffect(() => {
    announceCallback = (msg: string) => {
      // Clear first to ensure re-announcement of identical messages
      setMessage("")
      requestAnimationFrame(() => setMessage(msg))
    }

    return () => {
      announceCallback = null
    }
  }, [])

  return (
    <div
      aria-live="polite"
      role="status"
      className="sr-only"
    >
      {message}
    </div>
  )
}
