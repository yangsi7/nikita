import { cn } from "@/lib/utils"

interface SectionHeaderProps {
  children: React.ReactNode
  className?: string
}

export function SectionHeader({ children, className }: SectionHeaderProps) {
  return (
    <h2
      className={cn(
        "text-xs md:text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground",
        className
      )}
    >
      {children}
    </h2>
  )
}
