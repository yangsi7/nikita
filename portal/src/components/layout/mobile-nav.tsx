"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, TrendingUp, Sparkles, Heart, MessageSquare } from "lucide-react"
import { useIsMobile } from "@/hooks/use-mobile"
import { cn } from "@/lib/utils"

const tabs = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Engage", href: "/dashboard/engagement", icon: TrendingUp },
  { label: "Nikita", href: "/dashboard/nikita", icon: Sparkles },
  { label: "Vices", href: "/dashboard/vices", icon: Heart },
  { label: "Chat", href: "/dashboard/conversations", icon: MessageSquare },
] as const

export function MobileNav() {
  const isMobile = useIsMobile()
  const pathname = usePathname()

  if (!isMobile) return null

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 backdrop-blur-md bg-white/5 border-t border-white/10 pb-[env(safe-area-inset-bottom)]">
      <div className="flex items-center justify-around">
        {tabs.map((tab) => {
          const isActive =
            tab.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(tab.href)

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex flex-col items-center gap-0.5 py-2 px-3 min-h-11 min-w-11 justify-center",
                isActive ? "text-rose-400" : "text-muted-foreground"
              )}
            >
              <tab.icon className="h-5 w-5" />
              <span className="text-[10px] font-medium">{tab.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
