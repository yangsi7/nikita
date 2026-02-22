# Spec 062: Portal Visual Polish & Mobile

## Overview
Page transitions, animations, mobile bottom nav, skeleton shimmer, empty state CTAs, and touch optimization.

## Complexity: 0 (Solo /sdd)

## User Stories

### US-1: Page Transitions
- AnimatePresence wrapper for route changes
- Fade + subtle slide-up on page mount (opacity 0→1, y 8→0, 200ms)
- PageTransition component wrapping each page's content

### US-2: Modal/Drawer Animations
- Dialog/Sheet enter: scale 0.95→1 + fade in (150ms)
- Dialog/Sheet exit: scale 1→0.95 + fade out (100ms)
- Use Framer Motion variants

### US-3: Skeleton Shimmer
- Add CSS shimmer animation to LoadingSkeleton
- Gradient sweep from left to right (1.5s, infinite)
- Subtle: white/5 → white/10 → white/5

### US-4: Mobile Bottom Tab Navigation
- Show on mobile (< 768px) for player routes only
- 5 tabs: Dashboard, Engagement, Nikita, Vices, Conversations
- Active state with rose accent
- Hide sidebar on mobile, show bottom nav instead
- Fixed to bottom, glass-card background

### US-5: Touch Target Optimization
- Minimum 44x44px touch targets on all buttons/links on mobile
- Apply via Tailwind `min-h-11 min-w-11` on interactive elements

### US-6: Empty State CTAs
- Extend EmptyState component with optional `action` prop
- Action: { label: string, href?: string, onClick?: () => void }
- CTA button uses primary variant

### US-7: Custom Loading Spinner
- Branded spinner: rose-colored pulse ring
- Replace default Loader2 in sonner toasts
- Use in Suspense fallbacks

## Acceptance Criteria
- [ ] Pages animate on mount (fade + slide)
- [ ] Skeletons have shimmer animation
- [ ] Mobile shows bottom tab nav on player routes
- [ ] Bottom nav hides on admin routes
- [ ] EmptyState supports CTA buttons
- [ ] Touch targets >= 44px on mobile
- [ ] Portal builds with 0 TypeScript errors
- [ ] Framer Motion bundle impact < 15KB gzipped (already installed)
