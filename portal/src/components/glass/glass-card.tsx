import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { forwardRef } from "react"

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "elevated" | "danger" | "amber"
  children: React.ReactNode
}

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ variant = "default", className, children, ...props }, ref) => {
    const variantClass = {
      default: "glass-card",
      elevated: "glass-card-elevated",
      danger: "glass-card-danger",
      amber: "glass-card-amber",
    }[variant]

    return (
      <div ref={ref} className={cn(variantClass, className)} {...props}>
        {children}
      </div>
    )
  }
)
GlassCard.displayName = "GlassCard"

interface GlassCardWithHeaderProps extends GlassCardProps {
  title?: string
  description?: string
  action?: React.ReactNode
}

export function GlassCardWithHeader({
  title,
  description,
  action,
  variant,
  className,
  children,
  ...props
}: GlassCardWithHeaderProps) {
  return (
    <GlassCard variant={variant} className={cn("p-0", className)} {...props}>
      {(title || action) && (
        <div className="flex items-center justify-between p-6 pb-0">
          <div>
            {title && <h3 className="text-sm font-medium text-foreground">{title}</h3>}
            {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-6">{children}</div>
    </GlassCard>
  )
}
