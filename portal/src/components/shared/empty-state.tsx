import Link from "next/link"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Inbox } from "lucide-react"

interface EmptyStateProps {
  message: string
  description?: string
  icon?: React.ReactNode
  className?: string
  action?: { label: string; href?: string; onClick?: () => void }
}

export function EmptyState({ message, description, icon, className, action }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 py-12 text-center", className)}>
      {icon ?? <Inbox className="h-10 w-10 text-muted-foreground/50" />}
      <p className="text-sm font-medium text-muted-foreground">{message}</p>
      {description && <p className="text-xs text-muted-foreground/70">{description}</p>}
      {action && (
        action.href ? (
          <Button variant="default" asChild>
            <Link href={action.href}>{action.label}</Link>
          </Button>
        ) : (
          <Button variant="default" onClick={action.onClick}>
            {action.label}
          </Button>
        )
      )}
    </div>
  )
}
