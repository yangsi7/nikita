# Deployment Reference

## Cloud Run (Backend)

| Resource | Value |
|----------|-------|
| GCP Project | `gcp-transcribe-test` |
| GCP Account | `simon.yang.ch@gmail.com` |
| Cloud Run Service | `nikita-api` (region: `us-central1`) |
| Backend URL | `https://nikita-api-1040094048579.us-central1.run.app` |

**Deploy command:**
```bash
gcloud config set account simon.yang.ch@gmail.com && gcloud config set project gcp-transcribe-test
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated
```

**NEVER** set `--min-instances=1`. Must scale to zero. Cold starts (5-15s) are acceptable.
A PreToolUse hook (`guard-deploy.sh`) blocks `--min-instances` automatically.

## Vercel (Portal)

| Resource | Value |
|----------|-------|
| Portal URL | `https://portal-phi-orcin.vercel.app` |

**Deploy command:**
```bash
cd portal && npm run build && vercel --prod
```
