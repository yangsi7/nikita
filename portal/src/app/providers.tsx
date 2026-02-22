"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { Toaster } from "@/components/ui/sonner"
import { OfflineBanner } from "@/components/shared/offline-banner"
import { SkipLink } from "@/components/shared/skip-link"
import { SrAnnouncer } from "@/components/shared/sr-announcer"

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() =>
    new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          retry: 3,
          retryDelay: (attemptIndex) =>
            Math.min(1000 * 2 ** attemptIndex, 30000),
          refetchOnWindowFocus: false,
        },
      },
    })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <SkipLink />
      <OfflineBanner />
      <SrAnnouncer />
      {children}
      <Toaster
        richColors
        theme="dark"
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          classNames: {
            toast: "backdrop-blur-md bg-white/5 border-white/10",
          },
        }}
      />
    </QueryClientProvider>
  )
}
