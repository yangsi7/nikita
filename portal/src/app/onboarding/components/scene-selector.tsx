"use client"

// NOTE: Uses Radix RadioGroup directly instead of shadcn RadioGroup wrapper because
// each item is a full card with custom borders, backgrounds, and a Check icon indicator.
// The shadcn RadioGroupItem applies a fixed circular indicator style (size-4 rounded-full)
// that conflicts with this card-based layout.
import { RadioGroup as RadioGroupPrimitive } from "radix-ui"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const SCENES = [
  {
    value: "techno",
    emoji: "\uD83C\uDFA7",
    title: "Techno",
    description: "Dark clubs, warehouse raves",
  },
  {
    value: "art",
    emoji: "\uD83C\uDFA8",
    title: "Art",
    description: "Gallery openings, exhibitions",
  },
  {
    value: "food",
    emoji: "\uD83C\uDF7D\uFE0F",
    title: "Food",
    description: "Hidden gems, fine dining",
  },
  {
    value: "cocktails",
    emoji: "\uD83C\uDF78",
    title: "Cocktails",
    description: "Speakeasies, rooftops",
  },
  {
    value: "nature",
    emoji: "\uD83C\uDF3F",
    title: "Nature",
    description: "Hiking, beaches, outdoors",
  },
] as const

interface SceneSelectorProps {
  value: string | null
  onChange: (scene: string) => void
}

export function SceneSelector({ value, onChange }: SceneSelectorProps) {
  return (
    <RadioGroupPrimitive.Root
      value={value ?? ""}
      onValueChange={onChange}
      className="grid grid-cols-2 gap-3 md:flex md:gap-3"
      aria-label="Select your scene"
    >
      {SCENES.map((scene) => {
        const selected = value === scene.value
        return (
          <RadioGroupPrimitive.Item
            key={scene.value}
            value={scene.value}
            className={cn(
              "relative flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border p-4 text-center outline-none transition-[border-color,background-color] duration-150 ease-in-out",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              // Last card centered on mobile
              "last:col-span-2 last:mx-auto last:w-2/3 md:last:col-span-1 md:last:mx-0 md:last:w-auto",
              // flex-1 on desktop
              "md:flex-1",
              selected
                ? "border-rose-500 bg-rose-500/10 shadow-[0_0_15px_oklch(0.75_0.15_350/20%)]"
                : "border-white/10 bg-white/5 hover:border-white/20"
            )}
          >
            {selected && (
              <div className="absolute top-2 right-2">
                <Check className="size-3.5 text-rose-500" />
              </div>
            )}
            <span className="text-2xl" aria-hidden="true">
              {scene.emoji}
            </span>
            <span
              className={cn(
                "text-xs font-medium",
                selected ? "text-foreground" : "text-muted-foreground"
              )}
            >
              {scene.title}
            </span>
            <span className="text-[10px] leading-tight text-muted-foreground/60">
              {scene.description}
            </span>
          </RadioGroupPrimitive.Item>
        )
      })}
    </RadioGroupPrimitive.Root>
  )
}
