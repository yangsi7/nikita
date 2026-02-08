"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { Toaster } from "@/components/ui/sonner"

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() =>
    new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          retry: 1,
          refetchOnWindowFocus: false,
        },
      },
    })
  )

  return (
    <QueryClientProvider client={queryClient}>
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
