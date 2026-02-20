import { cn } from "@/lib/utils"

type SpinnerSize = "sm" | "md" | "lg"

const sizeClasses: Record<SpinnerSize, string> = {
  sm: "h-5 w-5",
  md: "h-8 w-8",
  lg: "h-12 w-12",
}

interface NikitaSpinnerProps {
  size?: SpinnerSize
  className?: string
}

export function NikitaSpinner({ size = "md", className }: NikitaSpinnerProps) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      <div className={cn("relative", sizeClasses[size])}>
        <div className="absolute inset-0 rounded-full border-2 border-rose-400/20" />
        <div className="absolute inset-0 rounded-full border-2 border-t-rose-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
      </div>
    </div>
  )
}
