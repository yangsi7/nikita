"use client"

import { useCallback, useState } from "react"
import { Button } from "@/components/ui/button"
import { X } from "lucide-react"

type PermissionState = "default" | "granted" | "denied" | "unsupported" | "dismissed"

/**
 * Push notification permission banner.
 * Shows when notifications are supported but not yet granted.
 * Dismissable — stores dismissal in localStorage.
 */
function getInitialPermissionState(): PermissionState {
  if (typeof window === "undefined") return "default"
  if (!("Notification" in window) || !("serviceWorker" in navigator)) return "unsupported"
  if (Notification.permission === "granted") return "granted"
  if (Notification.permission === "denied") return "denied"
  if (localStorage.getItem("nikita-push-dismissed")) return "dismissed"
  return "default"
}

export function PushPermissionBanner() {
  const [state, setState] = useState<PermissionState>(getInitialPermissionState)

  const handleEnable = useCallback(async () => {
    try {
      const permission = await Notification.requestPermission()
      if (permission === "granted") {
        setState("granted")
        await registerAndSubscribe()
      } else {
        setState("denied")
      }
    } catch {
      setState("denied")
    }
  }, [])

  const handleDismiss = useCallback(() => {
    localStorage.setItem("nikita-push-dismissed", "true")
    setState("dismissed")
  }, [])

  // Only show for "default" state
  if (state !== "default") return null

  return (
    <div className="relative flex items-center gap-3 rounded-lg border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm backdrop-blur-sm">
      <div className="flex-1">
        <p className="font-medium text-rose-300">Stay connected with Nikita</p>
        <p className="text-white/60">
          Enable notifications so you never miss a message
        </p>
      </div>
      <Button
        size="sm"
        variant="outline"
        className="border-rose-500/30 text-rose-300 hover:bg-rose-500/10"
        onClick={handleEnable}
      >
        Enable
      </Button>
      <button
        onClick={handleDismiss}
        className="absolute right-2 top-2 rounded p-1 text-white/40 hover:text-white/60"
        aria-label="Dismiss notification banner"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  )
}

/**
 * Register service worker and subscribe to push.
 */
async function registerAndSubscribe() {
  try {
    const registration = await navigator.serviceWorker.register("/sw.js")
    await navigator.serviceWorker.ready

    const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
    if (!vapidKey) {
      console.warn("[Push] NEXT_PUBLIC_VAPID_PUBLIC_KEY not configured")
      return
    }

    const keyArray = urlBase64ToUint8Array(vapidKey)
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyArray.buffer as ArrayBuffer,
    })

    // Send subscription to backend
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || ""
    await fetch(`${apiUrl}/api/v1/portal/push-subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        endpoint: subscription.endpoint,
        keys: {
          p256dh: arrayBufferToBase64(subscription.getKey("p256dh")),
          auth: arrayBufferToBase64(subscription.getKey("auth")),
        },
      }),
      credentials: "include",
    })
  } catch (err) {
    console.error("[Push] Registration failed:", err)
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/")
  const rawData = atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

function arrayBufferToBase64(buffer: ArrayBuffer | null): string {
  if (!buffer) return ""
  const bytes = new Uint8Array(buffer)
  let binary = ""
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}
