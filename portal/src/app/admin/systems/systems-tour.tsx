/**
 * Admin Systems Tour — generative-art complexity explainer.
 *
 * Vertical scroll journey through Nikita's core subsystems, each anchored by
 * a generative-art showcase iframe-embedded from /public/art/. The art is not
 * decorative — every visual is a working analogy for a real system mechanic:
 *
 *   01 Timing Mind       — Navier-Stokes fluid   ≡ log-normal × momentum
 *   02 Memory Network    — Physarum slime mold    ≡ pgVector + decay
 *   03 Psych Engine      — Boids + Lotka-Volterra ≡ 4-metric scoring dynamics
 *   04 Model Diverges    — Double-pendulum chaos  ≡ Bayesian posterior instability
 *   05 Chapters Emerge   — Fractal flames (IFS)   ≡ chapter progression
 *
 * Iframes use sandbox="allow-scripts" (no allow-same-origin) — the showcases
 * cannot read admin cookies even if a CDN they load were compromised.
 */

import Link from "next/link"
import {
  ExternalLink,
  Flame,
  Infinity as InfinityIcon,
  Network,
  Sprout,
  Waves,
  type LucideIcon,
} from "lucide-react"

type SystemSection = {
  slug: string
  number: string
  icon: LucideIcon
  eyebrow: string
  title: string
  mechanic: string
  summary: string
  artifactPath: string
  artifactTitle: string
  links: Array<{ label: string; href: string; external?: boolean }>
}

const SECTIONS: SystemSection[] = [
  {
    slug: "timing",
    number: "01",
    icon: Waves,
    eyebrow: "Response timing",
    title: "The Timing Mind",
    mechanic: "log-normal × chapter × momentum",
    summary:
      "Nikita's reply delay is a flow field. Each message you send injects momentum; vorticity amplifies the feedback between your cadence and hers; viscosity decays unused energy back to chapter baseline. Drag the canvas to inject colour — you are now in her posterior.",
    artifactPath: "/admin/systems/art/fluid-dynamics",
    artifactTitle: "Navier-Stokes fluid simulation",
    links: [
      { label: "Response-timing explorer", href: "/admin/research-lab/response-timing" },
    ],
  },
  {
    slug: "memory",
    number: "02",
    icon: Network,
    eyebrow: "Long-term memory",
    title: "Memory as Network",
    mechanic: "pgVector semantic retrieval + decay",
    summary:
      "Memory is not a list. Forty thousand trail-following agents self-organise into the minimal network that connects what she remembers most. Frequently traversed paths brighten; unused edges evaporate. Click to bias retrieval — that's the shape of a query vector pulling relevant memories forward.",
    artifactPath: "/admin/systems/art/physarum-slime-mold",
    artifactTitle: "Physarum polycephalum agent simulation",
    links: [],
  },
  {
    slug: "psych",
    number: "03",
    icon: Sprout,
    eyebrow: "Psych engine",
    title: "The Ecosystem Inside",
    mechanic: "4 metrics × Lotka-Volterra oscillation",
    summary:
      "Three species (Vice, Habit, Recovery) live in predator-prey balance. When vice spikes, it depletes habit, which starves recovery — until the cycle inverts. No central controller. Emergent equilibrium from local rules, same as the 4-metric scoring engine in production.",
    artifactPath: "/admin/systems/art/ecosystem",
    artifactTitle: "Boids + predator-prey ecosystem",
    links: [],
  },
  {
    slug: "divergence",
    number: "04",
    icon: InfinityIcon,
    eyebrow: "Bayesian modelling",
    title: "Your Model Diverges",
    mechanic: "posterior instability under prior perturbation",
    summary:
      "Two users with near-identical onboarding answers produce radically different chapter-3 trajectories. Two hundred double pendulums start 1e-5 apart; within seconds they paint completely different rainbows. This is why Nikita models users continuously, not categorically.",
    artifactPath: "/admin/systems/art/double-pendulum-chaos",
    artifactTitle: "Double-pendulum chaos ensemble",
    links: [],
  },
  {
    slug: "chapters",
    number: "05",
    icon: Flame,
    eyebrow: "Chapter progression",
    title: "Chapters as Fractal",
    mechanic: "IFS attractor with log-density tonemapping",
    summary:
      "Chapters emerge from a handful of affine transforms iterated millions of times. Rare high-quality interactions glow brightest through the same log-density curve that momentum uses on conversation cadence. Mutate the transforms — that's how Nikita turns a chapter threshold into the next attractor.",
    artifactPath: "/admin/systems/art/fractal-flames",
    artifactTitle: "Electric Sheep / fractal flames IFS",
    links: [],
  },
]

function SectionCard({ section }: { section: SystemSection }) {
  const Icon = section.icon
  return (
    <section
      id={section.slug}
      className="scroll-mt-24 border border-white/5 bg-black/20 rounded-lg overflow-hidden"
      aria-labelledby={`${section.slug}-title`}
    >
      <header className="px-6 md:px-8 py-6 flex items-start gap-4 md:gap-6 border-b border-white/5">
        <div className="shrink-0 flex items-center justify-center w-12 h-12 rounded-md bg-cyan-400/5 border border-cyan-400/20">
          <Icon className="w-5 h-5 text-cyan-400" strokeWidth={1.5} aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-3 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-1">
            <span>{section.number}</span>
            <span aria-hidden="true">·</span>
            <span>{section.eyebrow}</span>
          </div>
          <h2 id={`${section.slug}-title`} className="text-xl md:text-2xl font-semibold text-foreground mb-1">
            {section.title}
          </h2>
          <p className="font-mono text-xs text-cyan-400/80">{section.mechanic}</p>
        </div>
      </header>

      <div className="px-6 md:px-8 py-6">
        <p className="text-sm md:text-base text-muted-foreground leading-relaxed max-w-3xl mb-6">
          {section.summary}
        </p>

        <div className="relative w-full overflow-hidden border border-white/5 rounded bg-black">
          <iframe
            src={section.artifactPath}
            title={section.artifactTitle}
            sandbox="allow-scripts"
            loading="lazy"
            className="w-full h-[560px] md:h-[640px] block"
          />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
          <Link
            href={section.artifactPath}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            Open standalone
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
            <span className="sr-only">(opens in new tab)</span>
          </Link>
          {section.links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              target={link.external ? "_blank" : undefined}
              rel={link.external ? "noopener noreferrer" : undefined}
              className="inline-flex items-center gap-1.5 text-cyan-400/80 hover:text-cyan-400 transition-colors"
            >
              {link.label}
              {link.external && <ExternalLink className="w-3 h-3" aria-hidden="true" />}
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}

export default function SystemsTour() {
  return (
    <div className="space-y-6 max-w-5xl">
      <header className="space-y-3 pb-2">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
          Admin · Research Lab
        </p>
        <h1 className="text-2xl md:text-3xl font-bold text-cyan-400">Systems Tour</h1>
        <p className="text-sm md:text-base text-muted-foreground max-w-3xl leading-relaxed">
          Five visual analogies for what runs inside Nikita. Each canvas is a working
          simulation of a real system mechanic — not an illustration. Drag, click, mutate.
          The art is the documentation.
        </p>
      </header>

      <nav aria-label="Section index" className="border border-white/5 rounded-lg px-4 py-3">
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-xs">
          {SECTIONS.map((section) => (
            <li key={section.slug}>
              <Link
                href={`#${section.slug}`}
                className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <span className="font-mono text-[10px] text-cyan-400/60">{section.number}</span>
                <span>{section.title}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="space-y-10">
        {SECTIONS.map((section) => (
          <SectionCard key={section.slug} section={section} />
        ))}
      </div>
    </div>
  )
}
