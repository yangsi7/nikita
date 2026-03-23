import { GlassCard } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { MessageCircle } from "lucide-react"

export function DashboardEmptyState() {
  return (
    <GlassCard
      variant="elevated"
      className="mx-auto max-w-lg p-8 text-center"
      data-testid="dashboard-empty-state"
    >
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-rose-500/10">
          <MessageCircle className="h-7 w-7 text-rose-400" />
        </div>

        <h2 className="text-xl font-semibold text-foreground">
          Welcome to Nikita&apos;s World
        </h2>

        <p className="text-sm text-muted-foreground leading-relaxed">
          Start chatting with Nikita on Telegram to see your relationship stats
          here.
        </p>

        <Button asChild className="mt-2 bg-rose-500 hover:bg-rose-600 text-white">
          <a
            href="https://t.me/Nikita_my_bot"
            target="_blank"
            rel="noopener noreferrer"
          >
            <MessageCircle className="h-4 w-4" />
            Chat on Telegram
          </a>
        </Button>
      </div>
    </GlassCard>
  )
}
