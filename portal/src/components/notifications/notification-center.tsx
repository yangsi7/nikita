"use client"

import Link from "next/link"
import { Bell, CheckCheck, AlertTriangle, TrendingUp, BookOpen, Zap } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { Button } from "@/components/ui/button"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { useNotifications } from "@/hooks/use-notifications"
import type { PortalNotification } from "@/lib/api/types"

function notificationIcon(type: PortalNotification["type"]) {
  switch (type) {
    case "chapter_advance":
      return <BookOpen className="h-4 w-4 text-rose-400 shrink-0" />
    case "boss_encounter":
      return <Zap className="h-4 w-4 text-amber-400 shrink-0" />
    case "decay_warning":
      return <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
    case "engagement_shift":
      return <TrendingUp className="h-4 w-4 text-cyan-400 shrink-0" />
    default:
      return <Bell className="h-4 w-4 text-muted-foreground shrink-0" />
  }
}

interface NotificationItemProps {
  notification: PortalNotification
  onRead: (id: string) => void
}

function NotificationItem({ notification, onRead }: NotificationItemProps) {
  const content = (
    <div
      className={cn(
        "flex gap-3 px-4 py-3 transition-colors hover:bg-white/5 cursor-pointer",
        !notification.read && "border-l-2 border-rose-400"
      )}
      onClick={() => onRead(notification.id)}
    >
      <div className="mt-0.5">{notificationIcon(notification.type)}</div>
      <div className="flex-1 min-w-0">
        <p className={cn("text-sm leading-snug", notification.read ? "text-muted-foreground" : "text-foreground font-medium")}>
          {notification.title}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-snug line-clamp-2">
          {notification.message}
        </p>
        <p className="text-xs text-muted-foreground/60 mt-1">
          {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
        </p>
      </div>
    </div>
  )

  if (notification.actionHref) {
    return (
      <Link href={notification.actionHref} className="block">
        {content}
      </Link>
    )
  }

  return content
}

export function NotificationCenter() {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications()

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-8 w-8 text-muted-foreground hover:text-foreground"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white leading-none">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-80 p-0 border-white/10 bg-[oklch(0.13_0_0)] backdrop-blur-xl shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <span className="text-sm font-medium">Notifications</span>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1.5"
              onClick={markAllAsRead}
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all read
            </Button>
          )}
        </div>

        {/* Notification list */}
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center px-4">
            <Bell className="h-8 w-8 text-muted-foreground/40 mb-2" />
            <p className="text-sm text-muted-foreground">No notifications yet</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Events will appear here as they happen</p>
          </div>
        ) : (
          <ScrollArea className="max-h-80">
            <div className="divide-y divide-white/5">
              {notifications.map((n) => (
                <NotificationItem key={n.id} notification={n} onRead={markAsRead} />
              ))}
            </div>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  )
}
