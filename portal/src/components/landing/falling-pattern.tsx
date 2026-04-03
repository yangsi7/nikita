"use client"

// FallingPattern — Canvas-based matrix rain effect
// Adapted from portal/src/app/onboarding/components/ambient-particles.tsx

import { useRef, useEffect } from "react"

interface FallingPatternProps {
  className?: string
}

const CHARS = "abcdefghijklmnopqrstuvwxyzアイウエオカキクケコサシスセソタチツテト0123456789"
const FONT_SIZE = 14
const ROSE = "oklch(0.75 0.15 350 / 15%)"

export function FallingPattern({ className }: FallingPatternProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const mql = window.matchMedia("(prefers-reduced-motion: reduce)")
    const reducedMotion = mql.matches

    let columns = Math.floor(window.innerWidth / FONT_SIZE)
    let drops = Array<number>(columns).fill(1)

    function resize() {
      if (!canvas) return
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      columns = Math.floor(canvas.width / FONT_SIZE)
      drops = Array<number>(columns).fill(1)
    }
    resize()
    window.addEventListener("resize", resize)

    function drawFrame() {
      if (!ctx || !canvas) return
      ctx.fillStyle = "oklch(0.08 0 0 / 5%)"
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = ROSE
      ctx.font = `${FONT_SIZE}px "JetBrains Mono", monospace`

      for (let i = 0; i < drops.length; i++) {
        const char = CHARS[Math.floor(Math.random() * CHARS.length)]
        ctx.fillText(char, i * FONT_SIZE, drops[i] * FONT_SIZE)
        if (drops[i] * FONT_SIZE > canvas.height && Math.random() > 0.975) {
          drops[i] = 0
        }
        drops[i]++
      }
    }

    if (reducedMotion) {
      // Static single frame — no animation loop
      drawFrame()
    } else {
      function animate() {
        drawFrame()
        animationRef.current = requestAnimationFrame(animate)
      }
      animationRef.current = requestAnimationFrame(animate)
    }

    return () => {
      cancelAnimationFrame(animationRef.current)
      window.removeEventListener("resize", resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none fixed inset-0 z-0 ${className ?? ""}`}
      aria-hidden="true"
    />
  )
}
