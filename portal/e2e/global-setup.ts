import { test as setup } from "@playwright/test"
import path from "path"
import fs from "fs"

/**
 * Global setup: create auth storage states for authenticated tests.
 *
 * Since the portal uses Supabase magic link auth, we cannot programmatically
 * log in during tests. Instead, we create empty storage state files that tests
 * can reference. Tests that need auth will use route mocking or accept the
 * unauthenticated redirect behavior.
 *
 * If real auth is needed, set PLAYWRIGHT_USER_EMAIL and provide a session
 * token via environment variables.
 */

const AUTH_DIR = path.join(__dirname, ".auth")

const EMPTY_STORAGE_STATE = {
  cookies: [],
  origins: [],
}

setup("create auth storage states", async () => {
  // Ensure .auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true })
  }

  // Create player storage state (empty — tests handle auth via mocking/redirects)
  const playerPath = path.join(AUTH_DIR, "player.json")
  if (!fs.existsSync(playerPath)) {
    fs.writeFileSync(playerPath, JSON.stringify(EMPTY_STORAGE_STATE, null, 2))
  }

  // Create admin storage state (empty — tests handle auth via mocking/redirects)
  const adminPath = path.join(AUTH_DIR, "admin.json")
  if (!fs.existsSync(adminPath)) {
    fs.writeFileSync(adminPath, JSON.stringify(EMPTY_STORAGE_STATE, null, 2))
  }
})
