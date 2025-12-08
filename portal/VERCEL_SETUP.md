# Vercel Deployment Setup

## Prerequisites

- GitHub repository: `yangsi7/nikita`
- Vercel account (free tier works)
- Portal code in `portal/` directory

## Step 1: Connect GitHub Repository to Vercel

### 1.1 Import Project

1. **Visit Vercel** dashboard: https://vercel.com/new
2. **Click "Add New Project"**
3. **Select "Import Git Repository"**
4. **Search for** `yangsi7/nikita`
5. **Click "Import"**

### 1.2 Configure Project Settings

**Root Directory:**

- Set to: `portal`
- This tells Vercel to build from the `portal/` subdirectory

**Framework Preset:**

- Should auto-detect: **Next.js**
- If not, manually select "Next.js"

**Build Command:**

- Default: `pnpm build` (already configured in `vercel.json`)
- Leave as-is

**Output Directory:**

- Default: `.next`
- Leave as-is

**Install Command:**

- Default: `pnpm install`
- Leave as-is

### 1.3 Environment Variables

Add these environment variables in Vercel dashboard:

| Variable                        | Value                                         | Environment                      |
| ------------------------------- | --------------------------------------------- | -------------------------------- |
| `NEXT_PUBLIC_SUPABASE_URL`      | `https://vlvlwmolfdpzdfmtipji.supabase.co`    | Production, Preview, Development |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<your-anon-key>`                             | Production, Preview, Development |
| `NEXT_PUBLIC_API_URL`           | `https://nikita-api-<id>.us-central1.run.app` | Production, Preview, Development |

**How to add:**

1. Go to project settings → Environment Variables
2. Click "Add New"
3. Enter key, value, and select environments
4. Click "Save"

**Note:** For preview deployments, you may want to use different API URLs (e.g., staging backend).

### 1.4 Deploy

- Click **"Deploy"**
- Vercel will:
  - Clone the repository
  - Install dependencies
  - Build the Next.js app
  - Deploy to production

## Step 2: Automatic Preview Deployments

Once connected, Vercel automatically:

### 2.1 On Every PR

- ✅ Builds a preview deployment
- ✅ Generates unique URL: `nikita-portal-<hash>.vercel.app`
- ✅ Adds comment to PR with deployment link
- ✅ Updates comment on new commits

### 2.2 On Every Push to Branch

- ✅ Creates deployment for that branch
- ✅ Accessible at: `nikita-portal-<branch>.vercel.app`

### 2.3 On Merge to Main

- ✅ Deploys to production domain
- ✅ Updates custom domain (if configured)
- ✅ Previous deployment still accessible (instant rollback)

## Step 3: Configure Custom Domain (Optional)

1. **Go to** project settings → Domains
2. **Click "Add Domain"**
3. **Enter domain**: `portal.nikita.app` (or your choice)
4. **Follow DNS setup** instructions
5. **Verify** domain ownership

Vercel provides SSL certificate automatically.

## Step 4: GitHub Actions Integration

The repository already has `.github/workflows/portal-ci.yml` configured for:

- ✅ ESLint checks
- ✅ TypeScript type checking
- ✅ Prettier format checking
- ✅ Build verification

This runs **in addition to** Vercel's deployment, providing extra quality gates.

## Step 5: Vercel Project Settings

### Build & Development Settings

**✅ Automatically Import Environment Variables from linked Git Branch**

- Leave enabled (recommended)

**✅ Include source files outside of the Root Directory**

- Leave enabled for monorepo support

### Git Configuration

**✅ Production Branch:** `main`

- Deployments to `main` go to production

**✅ Preview Deployment Comments:** Enabled

- Vercel bot will comment on PRs

**✅ Deployment Notifications:** Enabled

- Get notified on deploy success/failure

## Step 6: Vercel CLI (Optional)

Install Vercel CLI for local development:

```bash
npm install -g vercel

# Link project
cd portal
vercel link

# Pull environment variables
vercel env pull .env.local

# Run local development with Vercel environment
vercel dev
```

## Deployment URLs

After setup, you'll have:

### Production

- **Main domain**: `nikita-portal.vercel.app`
- **Custom domain** (if configured): `portal.nikita.app`

### Preview (PR)

- **Format**: `nikita-portal-<pr-hash>-<team>.vercel.app`
- **Example**: `nikita-portal-git-feature-008-player-portal.vercel.app`

### Branch Deployments

- **Format**: `nikita-portal-<branch>-<team>.vercel.app`
- **Example**: `nikita-portal-develop.vercel.app`

## Monitoring & Logs

### View Deployment Logs

1. **Go to** Vercel dashboard → Project
2. **Click** on deployment
3. **View** build logs, function logs, errors

### Analytics (Pro Plan)

- Page views
- Performance metrics
- Core Web Vitals
- User geography

## Rollback & Redeploy

### Instant Rollback

1. **Go to** deployments list
2. **Find** previous successful deployment
3. **Click** "..." → "Promote to Production"
4. **Confirm** → Instant rollback (no rebuild needed)

### Redeploy

1. **Go to** deployment
2. **Click** "..." → "Redeploy"
3. **Choose** "Use existing Build Cache" or "Rebuild"

## Troubleshooting

### Build Fails

**Check:**

- Environment variables are set correctly
- `pnpm install` works locally
- `pnpm build` succeeds locally
- Root directory is set to `portal`

### Preview Deployment Not Created

**Check:**

- Vercel GitHub integration is installed
- Repository permissions are granted
- `.github/workflows` don't block Vercel

### Environment Variables Not Working

**Check:**

- Variables are prefixed with `NEXT_PUBLIC_` for client-side access
- Variables are added to correct environments (Production, Preview, Development)
- Redeploy after adding variables

## Security Best Practices

### ✅ DO:

- Use `NEXT_PUBLIC_` prefix ONLY for public variables
- Store sensitive keys (API keys, secrets) as server-side environment variables
- Enable "Git Fork Protection" in project settings
- Use different API URLs for preview vs production

### ❌ DON'T:

- Expose database credentials in `NEXT_PUBLIC_*` variables
- Commit `.env.local` to Git
- Use production API for preview deployments

## Cost Estimation

**Free Tier (Hobby):**

- Unlimited deployments
- 100 GB bandwidth/month
- 100 hours build time/month
- **Cost: $0**

**Pro Tier:**

- Unlimited deployments
- 1 TB bandwidth/month
- Unlimited build time
- Analytics & monitoring
- **Cost: $20/month**

## Next Steps

1. ✅ Connect repository to Vercel
2. ✅ Configure environment variables
3. ✅ Deploy to production
4. ✅ Test production deployment
5. ✅ Create first PR to test preview deployments
6. ✅ Configure custom domain (optional)
7. ✅ Set up monitoring & alerts

## Support

- **Vercel Docs**: https://vercel.com/docs
- **Next.js Docs**: https://nextjs.org/docs
- **Vercel Support**: https://vercel.com/help
