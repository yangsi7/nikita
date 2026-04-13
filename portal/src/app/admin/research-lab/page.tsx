import type { Metadata } from "next"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { FlaskConical } from "lucide-react"
import {
  MODELS,
  CATEGORY_ORDER,
  CATEGORY_LABELS,
  STATUS_VARIANTS,
  type ModelCategory,
  type ModelEntry,
} from "./models"

export const metadata: Metadata = {
  title: "Research Lab | Admin | Nikita",
  description: "Behavior model explorer for the Nikita AI system",
}

function ModelCard({ model }: { model: ModelEntry }) {
  return (
    <Link href={`/admin/research-lab/${model.slug}`} className="group block">
      <Card className="h-full transition-colors hover:border-cyan-400/40">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-sm font-semibold leading-snug group-hover:text-cyan-400 transition-colors">
              {model.title}
            </CardTitle>
            <Badge variant={STATUS_VARIANTS[model.status]} className="shrink-0 capitalize text-xs">
              {model.status}
            </Badge>
          </div>
          <Badge variant="outline" className="w-fit text-xs capitalize text-muted-foreground">
            {CATEGORY_LABELS[model.category]}
          </Badge>
        </CardHeader>
        <CardContent className="pb-2">
          <CardDescription className="text-xs leading-relaxed">{model.summary}</CardDescription>
        </CardContent>
        <CardFooter className="pt-2 border-t border-white/5">
          <p className="text-xs text-muted-foreground">Updated {model.updatedAt}</p>
        </CardFooter>
      </Card>
    </Link>
  )
}

export default function ResearchLabPage() {
  const grouped = CATEGORY_ORDER.reduce<Record<ModelCategory, ModelEntry[]>>(
    (acc, cat) => {
      acc[cat] = MODELS.filter((m) => m.category === cat)
      return acc
    },
    { timing: [], scoring: [], memory: [], personalization: [], other: [] }
  )

  const populatedCategories = CATEGORY_ORDER.filter((cat) => grouped[cat].length > 0)

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <FlaskConical className="h-6 w-6 text-cyan-400" />
        <div>
          <h1 className="text-xl font-bold text-cyan-400">Research Lab</h1>
          <p className="text-xs text-muted-foreground">
            Interactive behavior model explorer — {MODELS.length} model{MODELS.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {populatedCategories.map((cat) => (
        <section key={cat} aria-label={`${CATEGORY_LABELS[cat]} models`}>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-3">
            {CATEGORY_LABELS[cat]}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {grouped[cat].map((model) => (
              <ModelCard key={model.slug} model={model} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
