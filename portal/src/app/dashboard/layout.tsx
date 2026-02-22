"use client"

import { AppLayout } from "@/components/layout/sidebar"
import { ErrorBoundaryWrapper } from "@/components/shared/error-boundary-wrapper"
import { PushPermissionBanner } from "@/components/notifications/push-permission"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppLayout variant="player">
      <ErrorBoundaryWrapper>
        <PushPermissionBanner />
        <div id="main-content">{children}</div>
      </ErrorBoundaryWrapper>
    </AppLayout>
  )
}
