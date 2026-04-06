"use client"

import Image from "next/image"

const MOODS = [
  { src: "/images/nikita-moods/playful.png",    label: "playful" },
  { src: "/images/nikita-moods/intimate.png",   label: "intimate" },
  { src: "/images/nikita-moods/excited.png",    label: "excited" },
  { src: "/images/nikita-moods/cold.png",       label: "cold" },
  { src: "/images/nikita-moods/angry.png",      label: "angry" },
  { src: "/images/nikita-moods/stressed.png",   label: "stressed" },
  { src: "/images/nikita-moods/crying.png",     label: "crying" },
  { src: "/images/nikita-moods/frustrated.png", label: "frustrated" },
  { src: "/images/nikita-moods/lustful.png",    label: "lustful" },
] as const

export function MoodStrip() {
  return (
    <ul
      className="flex items-start gap-3"
      aria-label="Nikita's mood range — she's not the same person every day"
    >
      {MOODS.map((mood) => (
        <li key={mood.label} className="flex flex-col items-center gap-1 shrink-0">
          <div className="w-14 h-14 rounded-xl overflow-hidden border border-white/15 transition-colors hover:border-primary/60">
            <Image
              src={mood.src}
              alt={`Nikita — ${mood.label}`}
              width={56}
              height={56}
              className="object-cover w-full h-full"
              loading="lazy"
            />
          </div>
          <span className="text-[10px] tracking-widest uppercase text-muted-foreground">
            {mood.label}
          </span>
        </li>
      ))}
    </ul>
  )
}
