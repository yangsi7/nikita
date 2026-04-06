"use client"

import { motion } from "framer-motion"
import Image from "next/image"
import { TelegramMockup } from "./telegram-mockup"

export function PitchSection() {
  return (
    <section className="relative py-24 bg-background">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-12 lg:gap-16 items-center">
          {/* Left: mood portrait + caption */}
          <motion.div
            className="flex flex-col gap-6 items-center lg:items-start"
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <div className="relative w-full max-w-[420px] aspect-[3/4] rounded-2xl overflow-hidden border border-white/10">
              <Image
                src="/images/nikita-moods/intimate.png"
                alt="Nikita — in a rare quiet moment"
                fill
                className="object-cover mood-cycle-1"
                sizes="(max-width: 1024px) 100vw, 420px"
                loading="lazy"
              />
              <Image
                src="/images/nikita-moods/playful.png"
                alt="Nikita — playful"
                fill
                className="object-cover mood-cycle-2"
                sizes="(max-width: 1024px) 100vw, 420px"
                loading="lazy"
              />
              <Image
                src="/images/nikita-moods/cold.png"
                alt="Nikita — cold"
                fill
                className="object-cover mood-cycle-3"
                sizes="(max-width: 1024px) 100vw, 420px"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-background/60 via-transparent to-transparent pointer-events-none" />
            </div>
            <div className="text-center lg:text-left">
              <p className="text-2xl font-bold text-foreground leading-tight">
                She has a life.<br />
                She has opinions.<br />
                She&apos;ll let you know.
              </p>
            </div>
          </motion.div>

          {/* Right: extended Telegram conversation */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.15 }}
          >
            <TelegramMockup />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
