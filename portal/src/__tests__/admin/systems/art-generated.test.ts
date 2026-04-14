import { execSync } from "node:child_process"
import { readFileSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * Drift guard: the codegen at scripts/generate-art-module.mjs is wired into
 * predev/prebuild npm hooks, but `npm test` (vitest) does NOT trigger them.
 * If a developer edits src/app/admin/systems/_art/*.html and forgets to
 * regenerate (or vice versa), CI would silently pass against a stale
 * generated file. This test runs the codegen and asserts the committed
 * output is identical.
 */

describe("_art-generated.ts drift guard", () => {
  it("regenerating from _art/*.html produces the committed module byte-for-byte", () => {
    const generatedPath = join(
      process.cwd(),
      "src/app/admin/systems/_art-generated.ts",
    )
    const committed = readFileSync(generatedPath, "utf-8")

    execSync("node scripts/generate-art-module.mjs", { stdio: "pipe" })

    const regenerated = readFileSync(generatedPath, "utf-8")
    expect(regenerated).toBe(committed)
  })
})
