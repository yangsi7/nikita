---
description: Vercel domain canonical-redirect coupling with backend CORS allowlist
globs: ["nikita/config/**", "portal/vercel.json", ".env*", "docs/deployment.md"]
---

# Vercel Domain ↔ CORS Canonical Coupling

When Vercel redirects apex↔www (or any custom-domain redirect), the post-redirect domain is what the browser puts in the `Origin` header on subsequent API calls. The backend CORS allowlist MUST contain the **canonical** (post-redirect) domain, not the URL the user types.

## Mandatory pre-CORS check (3 commands)

Before adding/changing any entry in `nikita/config/settings.py:cors_origins` or `.env CORS_ORIGINS`:

```bash
# 1. Detect canonical via redirect-follow
curl -sI https://nikita-mygirl.com/ | grep -iE "(http/|location)"
curl -sI https://www.nikita-mygirl.com/ | grep -iE "(http/|location)"
# Expect ONE 200 + ONE 308/307 with Location pointing to the 200 host

# 2. Confirm Vercel redirect direction via REST API
TOKEN=$(jq -r .token "$HOME/Library/Application Support/com.vercel.cli/auth.json")
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.vercel.com/v9/projects/prj_mP2qGV9ICPdNilcT6Zrf18HY9O7p/domains/nikita-mygirl.com?teamId=team_tzoCYvqmW3v3OvvzyZOZ2VlT" \
  | jq '{name,redirect,redirectStatusCode}'

# 3. Verify CORS preflight from canonical domain reaches backend
curl -sI -H "Origin: https://nikita-mygirl.com" -X OPTIONS \
  "https://nikita-api-1040094048579.us-central1.run.app/api/v1/health" \
  | grep -iE "(http/|access-control-allow-origin)"
# Expect: 2xx + access-control-allow-origin matches the Origin header
```

If step 3 returns HTTP 400 or no `access-control-allow-origin` header, CORS list is wrong — fix before merge. PR #294 (Apr 16, 2026) precedent: apex was in CORS but Vercel redirected apex→www, would have broken every authenticated portal API call.

## Vercel CLI command catalog (memorized)

| Operation | Command |
|---|---|
| List domains in team | `vercel domains ls` |
| List aliases for project | `vercel alias ls` (filter `grep <project>`) |
| Inspect deployment + aliases | `vercel inspect <deployment-url>` (⚠ cached) |
| Add alias to deployment | `vercel alias set <deployment-url> <domain-or-subdomain>` |
| Remove alias | `vercel alias rm <alias> --yes` |
| List env vars | `vercel env ls` |
| Add env var | `vercel env add <NAME> <env>` (interactive) |
| Remove env var | `vercel env rm <NAME> <env> --yes` |
| List projects | `vercel project ls` |

`.vercel.app` subdomains are first-class: `vercel alias set <deployment> nikita-preview.vercel.app` works for any unclaimed name.

## Gotchas (PR #294 evidence)

- **Project rename ≠ alias cleanup**: renaming a Vercel project leaves all old auto-generated aliases (`portal-phi-orcin.vercel.app`, `portal-yangsi7s-projects.vercel.app`, etc.) attached to current production. After every rename, audit `vercel inspect <prod-deployment>` and `vercel alias rm` each stale entry.
- **`vercel inspect` is cached** after `vercel alias rm` — the alias list won't update for several minutes. Always verify removal via `curl -sI <removed-alias>` returning 404.
- **Apex+www both attached**: Vercel auto-creates one as canonical, the other as redirect. Default direction is unpredictable. Always set explicitly via REST API (see `vercel-rest-api.md`).

## Reference
- Cross-rule: `vercel-rest-api.md` for canonical-redirect direction changes
- Memory: `feedback_vercel_cors_canonical.md`
- Deployment doc: `docs/deployment.md` "Custom Domain Management"
