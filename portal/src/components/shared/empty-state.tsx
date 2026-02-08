import { cn } from "@/lib/utils"
import { Inbox } from "lucide-react"

interface EmptyStateProps {
  message: string
  description?: string
  icon?: React.ReactNode
  className?: string
}

export function EmptyState({ message, description, icon, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 py-12 text-center", className)}>
      {icon ?? <Inbox className="h-10 w-10 text-muted-foreground/50" />}
      <p className="text-sm font-medium text-muted-foreground">{message}</p>
      {description && <p className="text-xs text-muted-foreground/70">{description}</p>}
    </div>
  )
}
