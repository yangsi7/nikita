"use client"

import { useState } from "react"
import { Download } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { downloadExport } from "@/lib/export"
import { cn } from "@/lib/utils"

interface ExportButtonProps {
  /** Data type key passed to the export endpoint (e.g. "scores", "conversations") */
  type: string
  /** Button label text */
  label?: string
  /** Export file format */
  format?: "csv" | "json"
  /** Number of days of history to include */
  days?: number
  className?: string
}

export function ExportButton({
  type,
  label = "Export",
  format = "csv",
  days = 90,
  className,
}: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false)

  async function handleExport() {
    setIsExporting(true)
    try {
      await downloadExport(type, format, days)
      toast.success("Export downloaded", {
        description: `${type} data exported as ${format.toUpperCase()}`,
      })
    } catch {
      toast.error("Export failed", {
        description: "Please try again later.",
      })
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleExport}
      disabled={isExporting}
      className={cn(className)}
      aria-label={`Export ${type} data as ${format.toUpperCase()}`}
    >
      <Download className="mr-2 h-4 w-4" />
      {isExporting ? "Exporting..." : label}
    </Button>
  )
}
