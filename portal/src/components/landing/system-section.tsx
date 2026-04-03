"use client"

import { motion } from "framer-motion"
import { SystemTerminal } from "./system-terminal"

export function SystemSection() {
  return (
    <section className="relative py-24 bg-[oklch(0.06_0_0)]">
      <div className="container mx-auto px-6">
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl font-bold text-foreground mb-4">
            Under The Hood
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            This is not a chatbot. This is an engine.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="max-w-3xl mx-auto"
        >
          <SystemTerminal />
        </motion.div>
      </div>
    </section>
  )
}
