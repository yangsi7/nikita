import { cn } from "@/lib/utils"

interface NikitaQuoteProps {
  children: React.ReactNode
  className?: string
}

export function NikitaQuote({ children, className }: NikitaQuoteProps) {
  return (
    <blockquote
      className={cn(
        "text-sm md:text-base italic text-muted-foreground/80",
        className
      )}
    >
      {children}
      <cite className="block mt-1 not-italic text-xs text-muted-foreground/60">
        &mdash; Nikita
      </cite>
    </blockquote>
  )
}
