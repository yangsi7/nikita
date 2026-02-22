import { createBrowserClient } from "@supabase/ssr"
import { API_URL } from "@/lib/constants"

async function getExportToken(): Promise<string | null> {
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token ?? null
}

/**
 * Downloads an export file from the backend.
 * Triggers a browser file download for the given data type and format.
 *
 * @param type - Data type to export (e.g. "scores", "conversations")
 * @param format - File format: "csv" or "json"
 * @param days - Number of days of history to include (default 90)
 */
export async function downloadExport(
  type: string,
  format: "csv" | "json" = "csv",
  days = 90
): Promise<void> {
  const token = await getExportToken()
  const url = `${API_URL}/api/v1/portal/export/${type}?format=${format}&days=${days}`

  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: AbortSignal.timeout(60_000),
  })

  if (!response.ok) {
    throw new Error(`Export failed: ${response.status} ${response.statusText}`)
  }

  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = downloadUrl
  a.download = `nikita-${type}.${format}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(downloadUrl)
}
