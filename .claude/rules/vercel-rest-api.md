# Vercel REST API — Operations CLI Doesn't Expose

The Vercel CLI handles routine ops (alias set/rm, env add/rm, domains ls), but the REST API is required for things like canonical-redirect direction, project domain config patches, and bulk inspections. Per `feedback_infra_config_autonomy.md`: do this autonomously, don't offload to dashboard.

## Auth recipe (works from any session)

```bash
TOKEN=$(jq -r .token "$HOME/Library/Application Support/com.vercel.cli/auth.json")
TEAM_ID=$(curl -s -H "Authorization: Bearer $TOKEN" "https://api.vercel.com/v2/teams" \
  | jq -r '.teams[] | select(.slug=="5meo-inc") | .id')
PROJECT="prj_mP2qGV9ICPdNilcT6Zrf18HY9O7p"  # nikita-mygirl
```

## Endpoint matrix (most-used)

| Operation | Method | Path |
|---|---|---|
| Get domain config (incl. redirect) | GET | `/v9/projects/{projectId}/domains/{name}?teamId=…` |
| Set domain redirect direction | PATCH | `/v9/projects/{projectId}/domains/{name}?teamId=…` body `{"redirect":"<target>","redirectStatusCode":308}` |
| Remove domain redirect (make canonical) | PATCH | `/v9/projects/{projectId}/domains/{name}?teamId=…` body `{"redirect":null,"redirectStatusCode":null}` |
| List teams | GET | `/v2/teams` |
| List project deployments | GET | `/v6/deployments?projectId={projectId}&teamId=…` |
| Get specific deployment | GET | `/v13/deployments/{idOrUrl}?teamId=…` |
| List env vars | GET | `/v9/projects/{projectId}/env?teamId=…` |

## Worked example: flip apex↔www canonical (PR #294 precedent)

Goal: make apex `nikita-mygirl.com` canonical (no redirect), redirect www → apex with 308.

```bash
# 1. Remove redirect from apex
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"redirect":null,"redirectStatusCode":null}' \
  "https://api.vercel.com/v9/projects/$PROJECT/domains/nikita-mygirl.com?teamId=$TEAM_ID"

# 2. Add www → apex 308
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"redirect":"nikita-mygirl.com","redirectStatusCode":308}' \
  "https://api.vercel.com/v9/projects/$PROJECT/domains/www.nikita-mygirl.com?teamId=$TEAM_ID"

# 3. Verify with curl
curl -sI https://nikita-mygirl.com/  # → 200
curl -sI https://www.nikita-mygirl.com/  # → 308 + Location: https://nikita-mygirl.com/
```

## When to drop from CLI to REST API
- CLI command not found / not implemented (e.g., domain redirect direction)
- Need bulk inspection (e.g., audit all env vars across 5 projects)
- Need read-only programmatic access without state changes (CLI commands can have side effects)

## Reference
- Full Vercel REST API: https://vercel.com/docs/rest-api
- Project IDs: see `project_vercel_domain_state.md` memory
- Auth: `~/Library/Application Support/com.vercel.cli/auth.json` — token rotates if you re-login via CLI
