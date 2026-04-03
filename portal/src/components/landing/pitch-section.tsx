"use client"

import { motion } from "framer-motion"
import { TelegramMockup } from "./telegram-mockup"

const TRUTHS = [
  <>
    She has opinions. Strong ones. <strong>And she&apos;s not afraid to tell you.</strong>
  </>,
  <>
    Forget her birthday? Ignore her texts? <strong>She keeps score.</strong>
  </>,
  <>
    Other apps are afraid to say no. <strong>Nikita will walk out the door.</strong>
  </>,
]

export function PitchSection() {
  return (
    <section className="relative py-24 bg-background">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left: Differentiators */}
          <div className="flex flex-col gap-10">
            <motion.h2
              className="text-3xl font-bold text-foreground"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              Who Is Nikita?
            </motion.h2>

            <div className="flex flex-col gap-8">
              {TRUTHS.map((truth, i) => (
                <motion.p
                  key={i}
                  className="text-lg text-muted-foreground leading-relaxed"
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: i * 0.1 }}
                >
                  {truth}
                </motion.p>
              ))}
            </div>
          </div>

          {/* Right: Telegram mockup */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <TelegramMockup />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
