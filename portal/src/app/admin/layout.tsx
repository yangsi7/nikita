'use client'

import { ReactNode, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/supabase/client'
import { AdminNavigation } from '@/components/admin/AdminNavigation'
import { useIsAdmin } from '@/hooks/use-admin-data'
import Link from 'next/link'

export default function AdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  const { data: isAdmin, isLoading, error } = useIsAdmin()

  useEffect(() => {
    // Redirect non-admins to dashboard
    if (!isLoading && !isAdmin && !error) {
      router.push('/dashboard')
    }
  }, [isAdmin, isLoading, error, router])

  const handleLogout = async () => {
    await logout()
    router.push('/')
  }

  // Show loading state while checking admin status
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-4xl animate-pulse">🔐</div>
          <p className="text-lg text-muted-foreground">Verifying admin access...</p>
        </div>
      </div>
    )
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-4xl">⚠️</div>
          <p className="text-lg font-medium text-destructive">Access Error</p>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : 'Failed to verify access'}
          </p>
          <Button variant="outline" onClick={() => router.push('/')}>
            Go to Login
          </Button>
        </div>
      </div>
    )
  }

  // Redirect non-admins (useEffect handles this, but show placeholder)
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-4xl">🚫</div>
          <p className="text-lg font-medium">Admin Access Required</p>
          <p className="text-sm text-muted-foreground">Redirecting to dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/admin" className="text-2xl font-bold text-orange-500">
              Admin Debug
            </Link>
            <AdminNavigation />
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                ← Back to Portal
              </Button>
            </Link>
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
