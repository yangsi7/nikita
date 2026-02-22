"use client"

import { AppLayout } from "@/components/layout/sidebar"
import { ErrorBoundaryWrapper } from "@/components/shared/error-boundary-wrapper"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppLayout variant="admin">
      <ErrorBoundaryWrapper>
        <div id="main-content">{children}</div>
      </ErrorBoundaryWrapper>
    </AppLayout>
  )
}
