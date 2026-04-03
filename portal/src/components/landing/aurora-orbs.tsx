// AuroraOrbs — CSS-only animated background orbs (no framer-motion dependency)
// Animation driven by globals.css aurora-drift-1/2 keyframes

export function AuroraOrbs() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="aurora-orb aurora-orb-1" aria-hidden="true" />
      <div className="aurora-orb aurora-orb-2" aria-hidden="true" />
    </div>
  )
}
