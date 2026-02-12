"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { SocialCircleMember } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface FriendCardProps {
  friend: SocialCircleMember
}

export function FriendCard({ friend }: FriendCardProps) {
  const initials = friend.friend_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  return (
    <div
      className={cn(
        "rounded-lg bg-white/5 border border-white/10 p-4 space-y-3 transition-opacity",
        !friend.is_active && "opacity-50"
      )}
    >
      {/* Avatar and Name */}
      <div className="flex items-center gap-3">
        <Avatar>
          <AvatarFallback className="bg-rose-500/20 text-rose-300">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div>
          <h4 className="font-medium text-foreground">{friend.friend_name}</h4>
          <p className="text-xs text-muted-foreground">{friend.friend_role}</p>
        </div>
      </div>

      {/* Occupation */}
      {friend.occupation && (
        <div className="text-sm text-foreground/70">{friend.occupation}</div>
      )}

      {/* Personality */}
      {friend.personality && (
        <p className="text-sm text-foreground/60 italic">
          {friend.personality}
        </p>
      )}

      {/* Relationship to Nikita */}
      {friend.relationship_to_nikita && (
        <p className="text-sm text-muted-foreground">
          <span className="text-foreground/50">To Nikita:</span>{" "}
          {friend.relationship_to_nikita}
        </p>
      )}

      {/* Storyline Potential */}
      {friend.storyline_potential.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-2 border-t border-white/10">
          {friend.storyline_potential.map((potential, idx) => (
            <Badge
              key={idx}
              variant="outline"
              className="text-xs bg-white/5 border-rose-500/30"
            >
              {potential}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
