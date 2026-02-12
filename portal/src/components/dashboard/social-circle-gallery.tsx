"use client"

import { SocialCircleMember } from "@/lib/api/types"
import { FriendCard } from "./friend-card"

interface SocialCircleGalleryProps {
  friends: SocialCircleMember[]
}

export function SocialCircleGallery({ friends }: SocialCircleGalleryProps) {
  if (friends.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Nikita hasn't mentioned her friends yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">
          {friends.length} {friends.length === 1 ? "Friend" : "Friends"}
        </h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {friends.map((friend) => (
          <FriendCard key={friend.id} friend={friend} />
        ))}
      </div>
    </div>
  )
}
