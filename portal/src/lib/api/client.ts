import { createBrowserClient } from "@supabase/ssr"
import { API_URL } from "@/lib/constants"

async function getAuthToken(): Promise<string | null> {
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token ?? null
}

export async function apiClient<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken()
  const url = `${API_URL}/api/v1${path}`

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    signal: options.signal ?? AbortSignal.timeout(30000), // 30-second timeout
  })

  if (!response.ok) {
    // Global 401 handler — redirect to login
    if (response.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
    }

    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw { detail: error.detail ?? "Unknown error", status: response.status }
  }

  return response.json()
}

export const api = {
  get: <T>(path: string) => apiClient<T>(path),
  post: <T>(path: string, body?: unknown) =>
    apiClient<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body: unknown) =>
    apiClient<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) =>
    apiClient<T>(path, { method: "DELETE" }),
}
