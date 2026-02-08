"use client"

import { useParams } from "next/navigation"
import { useAdminUser } from "@/hooks/use-admin-user"
import { UserDetail } from "@/components/admin/user-detail"
import { GodModePanel } from "@/components/admin/god-mode-panel"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"

export default function AdminUserDetailPage() {
  const params = useParams()
  const id = params.id as string
  const { data: user, isLoading, error, refetch } = useAdminUser(id)

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={3} />
  if (error || !user) return <ErrorDisplay message="Failed to load user" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/admin">Admin</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbLink href="/admin/users">Users</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>{user.phone ?? (user.telegram_id ? `TG: ${user.telegram_id}` : user.id.slice(0, 8))}</BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <UserDetail user={user} />
      <GodModePanel userId={id} />
    </div>
  )
}
