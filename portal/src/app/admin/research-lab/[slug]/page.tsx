import { notFound } from "next/navigation"
import type { Metadata } from "next"
import fs from "fs/promises"
import path from "path"
import Link from "next/link"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeft, ExternalLink, FileCode, FileText, BookOpen } from "lucide-react"
import { MODELS, CATEGORY_LABELS, STATUS_VARIANTS } from "../models"

const GITHUB_BASE = "https://github.com/yangsim/nikita/blob/master"
const REPO_ROOT = path.join(process.cwd(), "..")

interface PageProps {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  return MODELS.map((m) => ({ slug: m.slug }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const model = MODELS.find((m) => m.slug === slug)
  if (!model) return { title: "Not Found" }
  return {
    title: `${model.title} | Research Lab | Nikita`,
    description: model.summary,
  }
}

async function readMarkdown(markdownPath: string): Promise<string | null> {
  try {
    const fullPath = path.join(REPO_ROOT, markdownPath)
    const content = await fs.readFile(fullPath, "utf-8")
    return content
  } catch {
    return null
  }
}

export default async function ResearchLabDetailPage({ params }: PageProps) {
  const { slug } = await params
  const model = MODELS.find((m) => m.slug === slug)
  if (!model) notFound()

  const markdownContent = model.markdownPath ? await readMarkdown(model.markdownPath) : null

  const hasLinks = model.codeRef || model.specRef || model.markdownPath

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Back navigation */}
      <Link
        href="/admin/research-lab"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-cyan-400 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Research Lab
      </Link>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold text-cyan-400">{model.title}</h1>
          <Badge variant={STATUS_VARIANTS[model.status]} className="capitalize">
            {model.status}
          </Badge>
          <Badge variant="outline" className="capitalize text-muted-foreground">
            {CATEGORY_LABELS[model.category]}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">Updated {model.updatedAt}</p>
        <p className="text-sm text-muted-foreground">{model.summary}</p>
      </div>

      {/* Links card */}
      {hasLinks && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">References</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {model.codeRef && (
              <a
                href={`${GITHUB_BASE}/${model.codeRef}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-cyan-400 transition-colors"
              >
                <FileCode className="h-3.5 w-3.5" />
                {model.codeRef}
              </a>
            )}
            {model.specRef && (
              <a
                href={`${GITHUB_BASE}/${model.specRef}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-cyan-400 transition-colors"
              >
                <FileText className="h-3.5 w-3.5" />
                {model.specRef}
              </a>
            )}
            {model.markdownPath && (
              <a
                href={`${GITHUB_BASE}/${model.markdownPath}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-cyan-400 transition-colors"
              >
                <BookOpen className="h-3.5 w-3.5" />
                {model.markdownPath}
              </a>
            )}
          </CardContent>
        </Card>
      )}

      {/* Interactive artifact iframe */}
      {model.artifactPath && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
              Interactive Explorer
            </h2>
            <Button variant="outline" size="sm" asChild>
              <a href={model.artifactPath} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                Open in new tab
              </a>
            </Button>
          </div>
          <iframe
            src={model.artifactPath}
            title={model.title}
            sandbox="allow-scripts"
            className="w-full h-[1800px] border border-border rounded-md"
          />
        </div>
      )}

      {/* Markdown documentation */}
      {model.markdownPath && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
            Documentation
          </h2>
          <Card>
            <CardContent className="pt-6">
              {markdownContent ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdownContent}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground italic">
                  Documentation not yet available. The model doc is being authored — check back soon.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
