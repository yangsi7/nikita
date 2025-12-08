'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', emoji: '🏠' },
  { name: 'History', href: '/history', emoji: '📊' },
  { name: 'Conversations', href: '/conversations', emoji: '💬' },
]

export function Navigation() {
  const pathname = usePathname()

  return (
    <nav className="flex items-center space-x-1">
      {navigation.map((item) => {
        const isActive = pathname === item.href
        return (
          <Link
            key={item.name}
            href={item.href}
            className={cn(
              'flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
              isActive
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            )}
          >
            <span>{item.emoji}</span>
            <span className="hidden md:inline">{item.name}</span>
          </Link>
        )
      })}
    </nav>
  )
}
