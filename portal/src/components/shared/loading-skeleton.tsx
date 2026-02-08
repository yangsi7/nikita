import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

type SkeletonVariant = "ring" | "chart" | "card-grid" | "table" | "kpi" | "card"

interface LoadingSkeletonProps {
  variant: SkeletonVariant
  className?: string
  count?: number
}

export function LoadingSkeleton({ variant, className, count = 3 }: LoadingSkeletonProps) {
  switch (variant) {
    case "ring":
      return (
        <div className={cn("flex flex-col items-center gap-3", className)}>
          <Skeleton className="h-[120px] w-[120px] rounded-full" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-16" />
        </div>
      )
    case "chart":
      return <Skeleton className={cn("h-[280px] w-full rounded-xl", className)} />
    case "card-grid":
      return (
        <div className={cn("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4", className)}>
          {Array.from({ length: count }).map((_, i) => (
            <Skeleton key={i} className="h-[140px] rounded-xl" />
          ))}
        </div>
      )
    case "table":
      return (
        <div className={cn("space-y-3", className)}>
          <Skeleton className="h-10 w-full rounded-lg" />
          {Array.from({ length: count }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )
    case "kpi":
      return <Skeleton className={cn("h-9 w-20", className)} />
    case "card":
      return <Skeleton className={cn("h-20 w-full rounded-lg", className)} />
    default:
      return <Skeleton className={cn("h-20 w-full", className)} />
  }
}
