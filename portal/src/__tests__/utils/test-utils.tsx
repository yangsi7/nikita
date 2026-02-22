import React from "react"
import { render, type RenderOptions } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi } from "vitest"
import type { UserStats, AdminUser } from "@/lib/api/types"

// -------------------------------------------------------------------
// QueryClient factory
// -------------------------------------------------------------------
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

// -------------------------------------------------------------------
// renderWithProviders
// -------------------------------------------------------------------
interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  queryClient?: QueryClient
}

export function renderWithProviders(
  ui: React.ReactElement,
  { queryClient = createTestQueryClient(), ...options }: RenderWithProvidersOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }
  return { ...render(ui, { wrapper: Wrapper, ...options }), queryClient }
}

// -------------------------------------------------------------------
// Mock factories
// -------------------------------------------------------------------
export function createMockUser(): UserStats {
  return {
    id: "user-123",
    relationship_score: 62,
    chapter: 2,
    chapter_name: "Getting Closer",
    boss_threshold: 75,
    progress_to_boss: 45,
    days_played: 14,
    game_status: "active",
    last_interaction_at: new Date().toISOString(),
    boss_attempts: 0,
    metrics: {
      intimacy: 0.6,
      passion: 0.55,
      trust: 0.7,
      secureness: 0.65,
      weights: { intimacy: 0.25, passion: 0.25, trust: 0.25, secureness: 0.25 },
    },
  }
}

export function createMockAdminUser(): AdminUser {
  return {
    id: "admin-456",
    telegram_id: "987654321",
    email: "admin@nanoleq.com",
    relationship_score: 80,
    chapter: 4,
    engagement_state: "IN_ZONE",
    game_status: "active",
    last_interaction_at: new Date().toISOString(),
    created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
  }
}

export function createMockSupabaseClient() {
  return {
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      signInWithOtp: vi.fn().mockResolvedValue({ data: {}, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
    },
    from: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    single: vi.fn().mockResolvedValue({ data: null, error: null }),
  }
}

// -------------------------------------------------------------------
// next/navigation mock (must be called inside vi.mock factory)
// -------------------------------------------------------------------
export const mockNextNavigation = {
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}
