import { createBrowserClient } from "@supabase/ssr"
import { API_URL } from "@/lib/constants"

async function getAuthToken(): Promise<string | null> {
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  // getUser() verifies the token with the Supabase server (not just local storage)
  const { error } = await supabase.auth.getUser()
  if (error) return null
  // After server-side verification, retrieve the access_token from the session
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
  post: <T>(
    path: string,
    body?: unknown,
    headers?: Record<string, string>,
    signal?: AbortSignal
  ) =>
    apiClient<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      headers,
      signal,
    }),
  put: <T>(path: string, body: unknown, headers?: Record<string, string>) =>
    apiClient<T>(path, { method: "PUT", body: JSON.stringify(body), headers }),
  patch: <T>(path: string, body: unknown, headers?: Record<string, string>) =>
    apiClient<T>(path, { method: "PATCH", body: JSON.stringify(body), headers }),
  delete: <T>(path: string) =>
    apiClient<T>(path, { method: "DELETE" }),
}
