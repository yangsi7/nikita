"use client"

import { AppLayout } from "@/components/layout/sidebar"
import { ErrorBoundaryWrapper } from "@/components/shared/error-boundary-wrapper"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppLayout variant="player">
      <ErrorBoundaryWrapper>
        <div id="main-content">{children}</div>
      </ErrorBoundaryWrapper>
    </AppLayout>
  )
}
