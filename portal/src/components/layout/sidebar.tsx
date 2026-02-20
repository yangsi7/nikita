"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarHeader,
  SidebarFooter, SidebarProvider, SidebarTrigger,
} from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import {
  LayoutDashboard, TrendingUp, Heart, MessageSquare, BookOpen,
  Settings, Users, Activity, Mic, MessageCircle, Cpu, BriefcaseBusiness,
  FileText, LogOut, Sparkles, BarChart3,
} from "lucide-react"
import { createClient } from "@/lib/supabase/client"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { MobileNav } from "./mobile-nav"
import { NotificationCenter } from "@/components/notifications/notification-center"

const playerItems = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { title: "Engagement", href: "/dashboard/engagement", icon: TrendingUp },
  { title: "Nikita's World", href: "/dashboard/nikita", icon: Sparkles },
  { title: "Vices", href: "/dashboard/vices", icon: Heart },
  { title: "Conversations", href: "/dashboard/conversations", icon: MessageSquare },
  { title: "Insights", href: "/dashboard/insights", icon: BarChart3 },
  { title: "Diary", href: "/dashboard/diary", icon: BookOpen },
  { title: "Settings", href: "/dashboard/settings", icon: Settings },
]

const adminItems = [
  { title: "Overview", href: "/admin", icon: LayoutDashboard },
  { title: "Users", href: "/admin/users", icon: Users },
  { title: "Voice", href: "/admin/voice", icon: Mic },
  { title: "Text", href: "/admin/text", icon: MessageCircle },
  { title: "Pipeline", href: "/admin/pipeline", icon: Cpu },
  { title: "Jobs", href: "/admin/jobs", icon: BriefcaseBusiness },
  { title: "Prompts", href: "/admin/prompts", icon: FileText },
]

interface AppSidebarProps {
  variant: "player" | "admin"
}

function AppSidebar({ variant }: AppSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const items = variant === "player" ? playerItems : adminItems
  const accentColor = variant === "player" ? "text-rose-400" : "text-cyan-400"

  async function handleLogout() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push("/login")
  }

  return (
    <Sidebar collapsible="icon" className="border-r border-white/5">
      <SidebarHeader className="p-4">
        <div className="flex items-center justify-between">
          <Link href={variant === "player" ? "/dashboard" : "/admin"} className="flex items-center gap-2">
            <span className={cn("text-lg font-bold", accentColor)}>Nikita</span>
            <span className="text-xs text-muted-foreground">
              {variant === "player" ? "Player" : "Admin"}
            </span>
          </Link>
          {variant === "player" && <NotificationCenter />}
        </div>
      </SidebarHeader>
      <Separator className="bg-white/5" />
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                const isActive = item.href === pathname ||
                  (item.href !== "/dashboard" && item.href !== "/admin" && pathname.startsWith(item.href))
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={item.href} className={cn(isActive && accentColor)}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-4">
        {variant === "admin" && (
          <Link href="/dashboard" className="mb-2">
            <Button variant="ghost" size="sm" className="w-full justify-start text-muted-foreground">
              <LayoutDashboard className="mr-2 h-4 w-4" />
              Player View
            </Button>
          </Link>
        )}
        <Button variant="ghost" size="sm" className="w-full justify-start text-muted-foreground" onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}

export function AppLayout({ variant, children }: { variant: "player" | "admin"; children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar variant={variant} />
      <main className="flex-1 overflow-auto">
        <div className="flex items-center gap-2 p-4 md:hidden">
          <SidebarTrigger />
        </div>
        <div className={cn("p-4 md:p-6 lg:p-8", variant === "player" && "pb-16 md:pb-0")}>{children}</div>
      </main>
      {variant === "player" && <MobileNav />}
    </SidebarProvider>
  )
}
