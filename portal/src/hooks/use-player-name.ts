"use client"

import { useQuery } from "@tanstack/react-query"
import { createClient } from "@/lib/supabase/client"

/**
 * Returns the display name for the authenticated player.
 * Fallback chain: user_profiles.name → email username → "You"
 */
export function usePlayerName(): string {
  const { data } = useQuery({
    queryKey: ["portal", "player-name"],
    queryFn: async () => {
      const supabase = createClient()
      const {
        data: { user },
      } = await supabase.auth.getUser()
      if (!user) return "You"

      const { data: profile } = await supabase
        .from("user_profiles")
        .select("name")
        .eq("id", user.id)
        .single()

      if (profile?.name) return profile.name
      if (user.email) return user.email.split("@")[0]
      return "You"
    },
    staleTime: 5 * 60 * 1000, // 5 min — name changes are rare
  })

  return data ?? "You"
}
