"use client"

import { useRef, useEffect, useCallback } from "react"

interface Particle {
  x: number
  y: number
  radius: number
  speed: number
  phase: number
  amplitude: number
}

function createParticles(width: number, height: number, count: number): Particle[] {
  return Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    radius: 1 + Math.random() * 2,
    speed: 0.15 + Math.random() * 0.35,
    phase: Math.random() * Math.PI * 2,
    amplitude: 10 + Math.random() * 20,
  }))
}

export function AmbientParticles() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)
  const particlesRef = useRef<Particle[]>([])
  const reducedMotionRef = useRef(false)

  const drawStatic = useCallback((ctx: CanvasRenderingContext2D, particles: Particle[]) => {
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
    for (const p of particles) {
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
      ctx.fillStyle = "oklch(0.75 0.15 350 / 8%)"
      ctx.fill()
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const mql = window.matchMedia("(prefers-reduced-motion: reduce)")
    reducedMotionRef.current = mql.matches

    function handleMotionChange(e: MediaQueryListEvent) {
      reducedMotionRef.current = e.matches
    }
    mql.addEventListener("change", handleMotionChange)

    function resize() {
      if (!canvas) return
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      particlesRef.current = createParticles(canvas.width, canvas.height, 35)

      if (reducedMotionRef.current && ctx) {
        drawStatic(ctx, particlesRef.current)
      }
    }

    resize()
    window.addEventListener("resize", resize)

    let time = 0

    function animate() {
      if (!ctx || !canvas) return

      if (reducedMotionRef.current) {
        drawStatic(ctx, particlesRef.current)
        return
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)
      time += 0.01

      for (const p of particlesRef.current) {
        // Slow upward drift
        p.y -= p.speed
        // Gentle sine wave horizontal movement
        const offsetX = Math.sin(time + p.phase) * p.amplitude * 0.02

        // Wrap around when particle drifts above canvas
        if (p.y + p.radius < 0) {
          p.y = canvas.height + p.radius
          p.x = Math.random() * canvas.width
        }

        ctx.beginPath()
        ctx.arc(p.x + offsetX, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = "oklch(0.75 0.15 350 / 8%)"
        ctx.fill()
      }

      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animationRef.current)
      window.removeEventListener("resize", resize)
      mql.removeEventListener("change", handleMotionChange)
    }
  }, [drawStatic])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      aria-hidden="true"
    />
  )
}
