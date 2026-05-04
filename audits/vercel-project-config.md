# Vercel Project Config (Authoritative)

Project: nikita-mygirl (`prj_mP2qGV9ICPdNilcT6Zrf18HY9O7p`, team `team_tzoCYvqmW3v3OvvzyZOZ2VlT`)

## Authoritative dashboard settings

NEVER edit these ad-hoc through the Vercel UI. PATCH them via REST API only, per
`.claude/rules/vercel-rest-api.md`.

| Field             | Value                                                  |
|-------------------|--------------------------------------------------------|
| `rootDirectory`   | `"portal"`                                             |
| `buildCommand`    | `null` (delegated to `portal/vercel.json`)             |
| `installCommand`  | `null` (delegated to `portal/vercel.json`)             |
| `outputDirectory` | `null` (delegated to Next.js default `.next`)          |
| `framework`       | `"nextjs"`                                             |
| `productionBranch`| `"master"`                                             |

## Source-of-truth file

`portal/vercel.json` is the source of truth for build commands, framework, headers,
and rewrites. It is version-controlled and the canonical place to edit those values.

Vercel does NOT support setting `rootDirectory` from a `vercel.json` file —
`rootDirectory` is a project-level setting only (per Vercel docs). That is why a
repo-root `vercel.json` is not used: Vercel reads `vercel.json` from inside the
configured `rootDirectory`, so a file at the repo root would only be read if
`rootDirectory` were unset.

## Drift history

- 2026-05-04: 14-deploy ERROR streak caused by dashboard `rootDirectory` drifting
  off `"portal"`. Re-PATCHed via REST API. This document codifies the canonical
  config so future drift is detectable.

## Verifying the live config

```bash
TOKEN=$(jq -r .token "$HOME/Library/Application Support/com.vercel.cli/auth.json")
TEAM_ID=team_tzoCYvqmW3v3OvvzyZOZ2VlT
PROJECT=prj_mP2qGV9ICPdNilcT6Zrf18HY9O7p

curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.vercel.com/v9/projects/$PROJECT?teamId=$TEAM_ID" \
  | jq '{rootDirectory, buildCommand, installCommand, outputDirectory, framework, productionBranch: .link.productionBranch}'
```

Expected output matches the table above.

## Related

- `.claude/rules/vercel-rest-api.md` — REST API recipes for Vercel ops
- `.claude/rules/vercel-cors-canonical.md` — CORS ↔ canonical-redirect coupling
- `portal/vercel.json` — build/headers/rewrites source of truth
- GH #482 — issue tracking this codification
