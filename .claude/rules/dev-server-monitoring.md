---
description: Proactively retrieve compile + browser errors when running a dev server (Next.js, Vite, FastAPI uvicorn)
globs: ["**"]
---

# Dev Server Monitoring

When you start a long-running dev server (Next.js + Turbopack, Vite, `uv run uvicorn`, `npm run dev`, `flutter run`, etc.) for the user, you OWN debugging that page until the user confirms it works. Do not declare the URL ready and stop.

## Two Error Surfaces — Monitor Both

| Surface | Where it shows | How to retrieve |
|---|---|---|
| **Compile / build errors** | Server stdout (Turbopack, Vite, uvicorn) | `tail` the background output file (path returned by Bash `run_in_background`) |
| **Browser runtime errors** (hydration, JS exceptions, React warnings, network 4xx/5xx, console.error) | Browser DevTools console / Network tab | `mcp__claude-in-chrome__navigate` then `mcp__claude-in-chrome__read_console_messages` and `mcp__claude-in-chrome__read_network_requests` |

The dev-server stdout will NOT surface hydration mismatches, client-side React warnings, or runtime JS exceptions. Those only appear in the browser. Tailing logs alone is insufficient.

## Required Sequence After Starting a Dev Server

1. **Start the server** — `Bash` with `run_in_background: true`, capture the output-file path.
2. **Wait for ready** — `ScheduleWakeup` or short poll until stdout shows `Ready` / `Local: http://...` / `Application startup complete`. Do not sleep blindly.
3. **Open the page in Chrome MCP** — `mcp__claude-in-chrome__navigate` to the target URL. (If the Chrome extension is not connected, ask the user to install/start it before declaring the URL ready.)
4. **Pull console errors** — `mcp__claude-in-chrome__read_console_messages` with `pattern: "(?i)error|warning|hydrat|failed"` to filter aggressively. Token-budget matters: never read the unfiltered console.
5. **Pull network failures** — `mcp__claude-in-chrome__read_network_requests` if any 4xx/5xx is plausible (auth pages, API pages, image/asset routes).
6. **Tail server stdout** — re-`tail` the background output file for late-arriving compile errors.
7. **If errors found, fix them BEFORE asking the user to look.** Do not wait for the user to paste the Next.js error overlay — you have direct programmatic access.
8. **Only after both surfaces are clean** report the URL with confidence.

## Anti-Pattern (avoid)

> "Dev server ready at http://localhost:PORT/route — go check it." (User opens browser, sees red error overlay, pastes the trace, you fix.)

This wastes a round-trip and signals you don't know the page actually works.

## Pattern (do this)

> Start server → wait ready → navigate Chrome MCP → read console (filtered) → read network if relevant → fix what's broken → THEN report URL.

## Common Errors to Filter For

- **Hydration mismatch** (`Math.random()` / `Date.now()` / `new Date()` in SSR'd Client Components) — fix with `useEffect` mount-guard or `next/dynamic({ ssr: false })`
- **`Failed to compile`** in Turbopack stdout — TS/syntax errors not surfaced in browser
- **Module not found** — missing dependency, missing path-alias mapping
- **CORS / CSP violations** — show in browser console only
- **Auth-redirect loops** — show as 302 chains in network tab

## Auth-Gated Dev Pages

For pages behind `/admin/*` or similar gates, set the auth-bypass env var (e.g., `E2E_AUTH_BYPASS=true E2E_AUTH_ROLE=admin` for portal) when starting the server, otherwise Chrome MCP navigation will redirect to `/login` and you will misread "no console errors" as "page works."

## Killing the Server

When the user says they're done reviewing, kill the background process explicitly via `KillShell` with the bash ID. Do not leave dev servers running across sessions — they squat ports.
